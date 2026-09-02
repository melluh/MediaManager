import asyncio
import logging
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from media_manager.common.import_scan_cache import (
    ImportScanMediaType,
    set_cached_importable_media,
)
from media_manager.common.import_sidecar import delete_import_sidecar
from media_manager.common.library_scan import (
    AdoptionOwner,
    MediaScanPlan,
    ScanRecord,
    ScanTarget,
    scan_media_targets,
)
from media_manager.common.media_files import (
    episode_file_stem,
    season_directory_name,
)
from media_manager.common.service import BaseMediaService
from media_manager.config import MediaManagerConfig, get_config
from media_manager.exceptions import ConflictError
from media_manager.metadataProvider.abstract_metadata_provider import (
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.dependencies import get_metadata_provider
from media_manager.metadataProvider.schemas import (
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.notification.service import NotificationService
from media_manager.schemas import MediaImportSuggestion
from media_manager.torrent.schemas import Quality, Torrent
from media_manager.torrent.service import TorrentService
from media_manager.torrent.utils import (
    get_files_for_import,
    get_torrent_filepath,
    import_file,
)
from media_manager.tv.metadata import TvMetadataService
from media_manager.tv.repository import TvRepository
from media_manager.tv.schemas import EpisodeFile, EpisodeId, Show

log = logging.getLogger(__name__)

# The season and episode a file is of, as written in its name. The only thing
# that decides which episode a loose file belongs to - directory names are too
# varied across hand-made libraries to be trusted.
SEASON_EPISODE_TOKEN = re.compile(r"S(\d+)E(\d+)", re.IGNORECASE)


class TvImportService(BaseMediaService[Show, Show]):
    def __init__(
        self,
        tv_repository: TvRepository,
        torrent_service: TorrentService,
        notification_service: NotificationService,
        tv_metadata_service: TvMetadataService,
    ) -> None:
        super().__init__(
            repository=tv_repository,
            torrent_service=torrent_service,
            indexer_service=None,  # type: ignore[arg-type]
            notification_service=notification_service,
        )
        self.tv_repository = tv_repository
        self.tv_metadata_service = tv_metadata_service

    def get_media_root_path(self, media: Show) -> Path:
        # Cached: a library-wide scan resolves one root per media item, and
        # re-parsing config.toml for each of them is pure waste.
        misc_config = get_config().misc
        return self.get_root_directory(
            media=media,
            default_dir=misc_config.tv_directory,
            libraries=misc_config.tv_libraries,
        )

    async def import_tv_show(
        self,
        show: Show,
        source_directory: Path,
        quality: Quality = Quality.unknown,
        torrent_id: str | None = None,
        file_path_suffix: str = "",
    ) -> bool:
        # Filesystem scan + archive extraction; offload off the event loop.
        video_files, _, _ = await asyncio.to_thread(
            get_files_for_import, directory=source_directory
        )
        if not video_files:
            return False

        any_imported = False
        for video_file in video_files:
            # Simple heuristic for season/episode from filename
            match = re.search(r"S(\d+)E(\d+)", video_file.name, re.IGNORECASE)
            if match:
                s_num, e_num = int(match.group(1)), int(match.group(2))
                season_dir_name = season_directory_name(s_num)
                season_dir = self.get_media_root_path(show) / season_dir_name
                season_dir.mkdir(parents=True, exist_ok=True)

                target_name = episode_file_stem(
                    show_name=show.name,
                    season_number=s_num,
                    episode_number=e_num,
                    file_path_suffix=file_path_suffix,
                )
                target_file = season_dir / f"{target_name}{video_file.suffix}"

                await asyncio.to_thread(
                    import_file, target_file=target_file, source_file=video_file
                )
                any_imported = True

                # Update DB
                try:
                    season = await self.tv_repository.get_season_by_number(
                        s_num, show.id
                    )
                    episode = next(
                        (e for e in season.episodes if e.number == e_num), None
                    )
                    if episode:
                        await self.tv_repository.add_episode_file(
                            EpisodeFile(
                                episode_id=episode.id,
                                quality=quality,
                                torrent_id=torrent_id,
                                file_path_suffix=file_path_suffix,
                                relative_path=str(
                                    Path(season_dir_name) / target_file.name
                                ),
                            )
                        )
                except Exception:
                    log.exception(f"Could not update DB for {video_file.name}")
        return any_imported

    async def import_torrent_files(self, torrent: Torrent, show: Show) -> None:
        success = await self.import_tv_show(
            show=show,
            source_directory=get_torrent_filepath(torrent),
            quality=torrent.quality,
            torrent_id=torrent.id,
        )
        if success:
            torrent.imported = True
            torrent.import_error = None
            await self.torrent_service.torrent_repository.save_torrent(torrent=torrent)
            await self.notify_import_success(show.name, "TV show")
        else:
            await self.notify_import_failure(torrent, show.name, "TV show")

    async def get_import_suggestion(
        self, tv_path: Path, metadata_provider: AbstractMetadataProvider
    ) -> MediaImportSuggestion:
        return await super().get_import_suggestion(
            directory=tv_path,
            metadata_provider=metadata_provider,
            search_func=self.tv_metadata_service.search_for_show,
            get_metadata_func=metadata_provider.get_show_metadata,
            get_images_func=metadata_provider.get_show_images,
            media_type=MediaType.tv,
        )

    async def get_import_candidates(
        self, tv_path: Path, metadata_provider: AbstractMetadataProvider
    ) -> list[MetaDataProviderSearchResult]:
        return await super().get_import_candidates(
            directory=tv_path,
            metadata_provider=metadata_provider,
            search_func=self.tv_metadata_service.search_for_show,
        )

    def build_scan_target(
        self,
        show: Show,
        files_by_episode: Mapping[EpisodeId, Sequence[EpisodeFile]],
    ) -> ScanTarget:
        """
        The scan target for one show, shared by the library-wide scan and by
        the single-show scan an import runs.

        :param show: The show to scan.
        :param files_by_episode: Existing episode file records, keyed by
            episode; entries for other shows are ignored.
        :return: The target describing what to look for and what is on record.
        """
        show_root = self.get_media_root_path(media=show)
        episodes_by_number = {
            (season.number, episode.number): (season.number, episode)
            for season in show.seasons
            for episode in season.episodes
        }

        def adopt(path: Path) -> AdoptionOwner | None:
            # Both numbers come from the file's own SxxEyy token, wherever the
            # file sits: a hand-made library may file season 1 under "Season
            # 01", "S01" or nothing at all. Anything that doesn't resolve to an
            # episode we already know about is left alone rather than turned
            # into an invented episode.
            match = SEASON_EPISODE_TOKEN.search(path.name)
            if match is None:
                return None
            found = episodes_by_number.get(
                (int(match.group(1)), int(match.group(2)))
            )
            if found is None:
                return None
            season_number, episode = found
            return AdoptionOwner(
                key=episode.id,
                canonical_stem=episode_file_stem(
                    show_name=show.name,
                    season_number=season_number,
                    episode_number=episode.number,
                ),
            )

        return ScanTarget(
            media_root=show_root,
            records=[
                ScanRecord(
                    owner_key=episode.id,
                    stem=episode_file_stem(
                        show_name=show.name,
                        season_number=season.number,
                        episode_number=episode.number,
                        file_path_suffix=episode_file.file_path_suffix,
                    ),
                    file_path_suffix=episode_file.file_path_suffix,
                    relative_path=episode_file.relative_path,
                )
                for season in show.seasons
                for episode in season.episodes
                for episode_file in files_by_episode.get(episode.id, [])
            ],
            adopt=adopt,
        )

    async def apply_scan_plan(self, plan: MediaScanPlan) -> None:
        """
        Writes what a scan decided for one show. The episode each change
        belongs to is carried on the plan itself, so the show is not needed.

        :param plan: The changes the scan planned.
        """
        for path_update in [*plan.relinked, *plan.cleared]:
            await self.tv_repository.set_episode_file_relative_path(
                episode_id=EpisodeId(path_update.record.owner_key),
                file_path_suffix=path_update.record.file_path_suffix,
                relative_path=path_update.relative_path,
            )
        for adoption in plan.adoptions:
            await self.tv_repository.add_episode_file(
                episode_file=EpisodeFile(
                    episode_id=EpisodeId(adoption.owner_key),
                    quality=adoption.quality,
                    torrent_id=None,
                    file_path_suffix=adoption.file_path_suffix,
                    relative_path=adoption.relative_path,
                )
            )

    async def scan_show_files(self, show: Show) -> MediaScanPlan:
        """
        Scans a single show's directory and applies what it finds.

        :param show: The show to scan.
        :return: The changes that were applied.
        """
        files_by_episode = await self.tv_repository.get_episode_files_by_show_id(
            show_id=show.id
        )
        target = self.build_scan_target(show=show, files_by_episode=files_by_episode)
        plan = (await scan_media_targets([target]))[0]
        await self.apply_scan_plan(plan=plan)
        return plan

    async def import_existing_tv_show(
        self, tv_show: Show, source_directory: Path
    ) -> bool:
        """
        Adopts a show that is already on disk, without moving a single file:
        the show is pointed at the directory the user already has, and a scan
        of that directory records the episode files in it.

        :param tv_show: The show to attach the existing directory to.
        :param source_directory: The directory the show's files are in.
        :return: Whether any file was adopted.
        :raises ConflictError: If the show already has episode file records,
            which re-pointing its directory would orphan, or if the directory
            does not sit in the library the show is assigned to.
        """
        existing_files = await self.tv_repository.get_episode_files_by_show_id(
            show_id=tv_show.id
        )
        if existing_files:
            msg = (
                f"{tv_show.name} already has files in the library; "
                "importing an existing directory would orphan them."
            )
            raise ConflictError(msg)

        # The parent of a media item's directory comes from its library, while
        # the import source always sits in the default root. If those disagree
        # the scan would look in a directory that does not exist, so refuse
        # before storing a directory name that points nowhere.
        expected_root = self.get_media_root_path(
            media=tv_show.model_copy(update={"directory_name": source_directory.name})
        )
        if expected_root != source_directory:
            msg = (
                f"{tv_show.name} is assigned to the '{tv_show.library}' library, "
                f"which does not contain {source_directory}. Move the directory "
                f"into that library, or reassign the show to the default library."
            )
            raise ConflictError(msg)

        await self.tv_repository.set_directory_name(
            entity_id=tv_show.id, directory_name=source_directory.name
        )
        # The scan resolves the show's root from its directory name, so it has
        # to see the name that was just stored rather than the stale one.
        tv_show = tv_show.model_copy(update={"directory_name": source_directory.name})

        plan = await self.scan_show_files(show=tv_show)
        if plan.adoptions:
            log.info(
                f"Imported {tv_show.name} in place from {source_directory}: "
                f"{len(plan.adoptions)} file(s) adopted"
            )
            # The directory now belongs to a media item, so the scan will skip
            # it from here on and its cached match is dead weight.
            await asyncio.to_thread(delete_import_sidecar, source_directory)
        return bool(plan.adoptions)

    async def get_importable_tv_shows(
        self, metadata_provider: AbstractMetadataProvider
    ) -> list[MediaImportSuggestion]:
        return await self.get_importable_media(
            root_path=MediaManagerConfig().misc.tv_directory,
            metadata_provider=metadata_provider,
            get_suggestion_func=self.get_import_suggestion,
        )

    async def rescan_importable_tv_shows(self) -> list[MediaImportSuggestion]:
        """
        Re-scans the TV directory for importable shows and refreshes the
        cache read by the `/importable` endpoint. Always scans with the
        default (tmdb) metadata provider, matching what the frontend requests.
        """
        suggestions = await self.get_importable_tv_shows(
            metadata_provider=get_metadata_provider()
        )
        set_cached_importable_media(ImportScanMediaType.tv, suggestions)
        return suggestions

    async def import_all_torrents(self) -> None:
        await self.import_all_torrents_base(
            get_media_func=self.torrent_service.get_show_of_torrent,
            import_torrent_func=self.import_torrent_files,
            media_type_name="tv show",
        )
