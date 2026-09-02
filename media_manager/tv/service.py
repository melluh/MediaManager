import asyncio
import shutil
from collections.abc import Sequence
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from media_manager.common.downloaded_status_cache import (
    DownloadedMediaType,
    get_cached_downloaded,
    set_cached_downloaded_statuses,
)
from media_manager.common.library_scan import (
    LibraryScanCounts,
    count_plans,
    scan_media_targets,
)
from media_manager.common.media_files import (
    MediaFileLocation,
    attach_media_file_details,
    episode_file_stem,
    season_directory_name,
)
from media_manager.common.service import BaseMediaService
from media_manager.config import get_config
from media_manager.indexer.schemas import IndexerQueryResult, IndexerQueryResultId
from media_manager.indexer.scoring import slot_and_score_results
from media_manager.indexer.service import IndexerService
from media_manager.notification.service import NotificationService
from media_manager.torrent.schemas import (
    Torrent,
)
from media_manager.torrent.service import TorrentService
from media_manager.tv import log
from media_manager.tv.importer import TvImportService
from media_manager.tv.metadata import TvMetadataService
from media_manager.tv.repository import TvRepository
from media_manager.tv.schemas import (
    Episode,
    EpisodeFile,
    EpisodeId,
    EpisodeNumber,
    PublicEpisodeFile,
    PublicSeason,
    PublicShow,
    RichSeasonTorrent,
    RichShowTorrent,
    Season,
    SeasonId,
    Show,
    ShowId,
    ShowSummary,
)


class TvService(BaseMediaService[Show, Show]):
    def __init__(
        self,
        tv_repository: TvRepository,
        torrent_service: TorrentService,
        indexer_service: IndexerService,
        notification_service: NotificationService,
        tv_import_service: TvImportService,
        tv_metadata_service: TvMetadataService,
    ) -> None:
        super().__init__(
            repository=tv_repository,
            torrent_service=torrent_service,
            indexer_service=indexer_service,
            notification_service=notification_service,
        )
        self.tv_repository = tv_repository
        self.tv_import_service = tv_import_service
        self.tv_metadata_service = tv_metadata_service

    async def get_total_downloaded_episodes_count(self) -> int:
        """
        Get total number of downloaded episodes.
        """

        return await self.tv_repository.get_total_downloaded_episodes_count()

    async def set_show_library(self, show: Show, library: str) -> None:
        await self.tv_repository.set_show_library(show.id, library)

    async def get_all_shows(self) -> list[ShowSummary]:
        """
        Get all shows in the library, without their seasons/episodes.
        """
        return await self.attach_media_images_many(
            await self.tv_repository.get_shows_summary()
        )

    async def delete_show(
        self,
        show: Show,
        delete_files_on_disk: bool = False,
        delete_torrents: bool = False,
    ) -> None:
        """
        Delete a show from the database, optionally deleting files and torrents.

        :param show: The show to delete.
        :param delete_files_on_disk: Whether to delete the show's files from disk.
        :param delete_torrents: Whether to delete associated torrents from the torrent client.
        """
        if delete_files_on_disk or delete_torrents:
            log.debug(f"Deleting ID: {show.id} - Name: {show.name}")

            if delete_files_on_disk:
                show_dir = self.get_root_show_directory(show=show)

                log.debug(f"Attempt to delete show directory: {show_dir}")
                if show_dir.exists() and show_dir.is_dir():
                    await asyncio.to_thread(shutil.rmtree, show_dir)
                    log.info(f"Deleted show directory: {show_dir}")

            if delete_torrents:
                torrents = await self.tv_repository.get_torrents_by_show_id(show_id=show.id)
                for torrent in torrents:
                    try:
                        await self.torrent_service.cancel_download(torrent, delete_files=True)
                        await self.torrent_service.delete_torrent(torrent_id=torrent.id)
                        log.info(f"Deleted torrent: {torrent.hash}")
                    except Exception:  # noqa: BLE001 # best-effort cleanup, continue on any failure
                        log.warning(
                            f"Failed to delete torrent {torrent.hash}", exc_info=True
                        )

        await self.tv_repository.delete_show(show.id)

    async def get_public_episode_files_by_season_id(
        self, season: Season
    ) -> list[PublicEpisodeFile]:
        """
        Get all public episode files for a given season, enriched with their
        resolved path on disk and the details probed from the file itself.

        :param season: The season object.
        :return: A list of public episode files.
        """
        episode_files = await self.tv_repository.get_episode_files_by_season_id(
            season_id=season.id
        )
        public_episode_files = [
            PublicEpisodeFile.model_validate(x) for x in episode_files
        ]
        for episode_file in public_episode_files:
            exists = await self.episode_file_exists_on_file(episode_file=episode_file)
            episode_file.downloaded = exists
            episode_file.imported = exists

        show = await self.tv_repository.get_show_summary_by_season_id(
            season_id=season.id
        )
        episode_numbers_by_id = {
            episode.id: episode.number for episode in season.episodes
        }
        # A file whose episode isn't part of this season can't be located, so
        # it is left without a path rather than pointed at a made-up one.
        locatable = [
            (episode_file, episode_numbers_by_id[episode_file.episode_id])
            for episode_file in public_episode_files
            if episode_file.episode_id in episode_numbers_by_id
        ]
        await attach_media_file_details(
            [episode_file for episode_file, _ in locatable],
            [
                self.get_episode_file_location(
                    show=show,
                    season_number=season.number,
                    episode_number=episode_number,
                    episode_file=episode_file,
                )
                for episode_file, episode_number in locatable
            ],
        )
        return public_episode_files

    def get_episode_file_location(
        self,
        show: ShowSummary,
        season_number: int,
        episode_number: int,
        episode_file: EpisodeFile,
    ) -> MediaFileLocation:
        """
        Where an episode file is expected on disk: inside the show's season
        directory, named after the show and its season/episode numbers,
        reported relative to the parent TV folder (the default TV directory,
        or the show's library root if it belongs to one).
        """
        show_root_path = self.get_root_show_directory(show=show)
        return MediaFileLocation(
            directory=show_root_path / season_directory_name(season_number),
            stem=episode_file_stem(
                show_name=show.name,
                season_number=season_number,
                episode_number=episode_number,
                file_path_suffix=episode_file.file_path_suffix,
            ),
            relative_to=show_root_path.parent,
            media_root=show_root_path,
        )

    async def scan_library_files(self) -> LibraryScanCounts:
        """
        Reconcile every show's episode file records with the files on disk:
        relink records that lost track of their file, clear the path of records
        whose file is gone, and adopt video files sitting anywhere under the
        show's directory without a record of their own.

        Shows whose root directory does not exist are skipped untouched - a
        library that isn't mounted must not be mistaken for a library that
        emptied itself.

        :return: What the scan changed.
        """
        shows = await self.tv_repository.get_shows()
        files_by_episode = (
            await self.tv_repository.get_all_episode_files_grouped_by_episode()
        )
        plans = await scan_media_targets(
            [
                self.tv_import_service.build_scan_target(
                    show=show, files_by_episode=files_by_episode
                )
                for show in shows
            ]
        )
        for plan in plans:
            await self.tv_import_service.apply_scan_plan(plan=plan)

        counts = count_plans(plans)
        log.info(
            f"TV library scan: {counts.items_scanned} scanned, "
            f"{counts.items_skipped} skipped (directory missing), "
            f"{counts.paths_relinked} paths relinked, "
            f"{counts.paths_cleared} paths cleared, "
            f"{counts.files_adopted} files adopted"
        )
        return counts

    async def get_all_available_torrents_for_a_season(
        self,
        season_number: int,
        show_id: ShowId,
        search_query_override: str | None = None,
        allow_language_variants: list[str] | None = None,
    ) -> list[IndexerQueryResult]:
        """
        Get all available torrents for a given season.

        :param season_number: The number of the season.
        :param show_id: The ID of the show.
        :param search_query_override: Optional override for the search query.
        :param allow_language_variants: Language variants (e.g. "multi",
            "dubbed") to allow for this search on top of the configured
            defaults.
        :return: A list of indexer query results.
        """

        if search_query_override:
            return await self.indexer_service.search(query=search_query_override, is_tv=True)

        show = await self.tv_repository.get_show_by_id(show_id=show_id)

        torrents = await self.indexer_service.search_season(
            show=show, season_number=season_number
        )

        results = [torrent for torrent in torrents if season_number in torrent.season]

        def episode_count_for_torrent(result: IndexerQueryResult) -> int | None:
            # A single-episode release (S01E05) covers one episode, not the
            # whole season - only fall back to the season's full episode
            # count for season packs (result.episode empty).
            if result.episode:
                return len(result.episode)
            count = sum(
                len(season.episodes)
                for season in show.seasons
                if season.number in result.season
            )
            return count or None

        return slot_and_score_results(
            is_tv=True,
            results=results,
            media=show,
            episode_count_for_torrent=episode_count_for_torrent,
            allow_language_variants=allow_language_variants,
        )

    async def get_public_show_by_id(self, show: Show) -> PublicShow:
        """
        Get a public show from a Show object.

        :param show: The show object.
        :return: A public show.
        """
        public_show = PublicShow.model_validate(show)
        public_seasons: list[PublicSeason] = []

        for season in show.seasons:
            public_season = PublicSeason.model_validate(season)

            for episode in public_season.episodes:
                episode.downloaded = await self.is_episode_downloaded(
                    episode_id=episode.id
                )

            # A season is considered downloaded if it has episodes and all of them are downloaded.
            public_season.downloaded = bool(public_season.episodes) and all(
                episode.downloaded for episode in public_season.episodes
            )
            public_seasons.append(public_season)

        public_show.seasons = await self.attach_media_images_many(public_seasons)
        return await self.attach_media_images(public_show)

    async def get_show_by_id(self, show_id: ShowId) -> Show:
        """
        Get a show by its ID.

        :param show_id: The ID of the show.
        :return: The show.
        """
        return await self.tv_repository.get_show_by_id(show_id=show_id)

    async def get_show_by_slug(self, slug: str) -> Show:
        """
        Get a show by its slug.

        :param slug: The slug of the show.
        :return: The show.
        """
        return await self.tv_repository.get_show_by_slug(slug=slug)

    async def is_episode_downloaded(self, episode_id: EpisodeId) -> bool:
        """
        Check if an episode is downloaded and imported (file exists on disk).

        Reads the shared cache populated by the periodic
        `rescan_downloaded_episodes` scan, so this never touches the
        filesystem or the database on the request path. If the scan hasn't
        run yet (e.g. briefly after startup), falls back to a cheap DB-only
        signal (does the episode have any file record, and is it imported).

        :param episode_id: The ID of the episode.
        :return: True if the episode is downloaded and imported, False otherwise.
        """
        cached = get_cached_downloaded(DownloadedMediaType.episode, episode_id)
        if cached is not None:
            return cached

        episode_files = await self.tv_repository.get_episode_files_by_episode_id(
            episode_id=episode_id
        )
        for episode_file in episode_files:
            if await self.episode_file_exists_on_file(episode_file=episode_file):
                return True
        return False

    async def rescan_downloaded_episodes(self) -> None:
        """
        Recompute which episodes are downloaded by checking each season's
        directory on disk once, and refresh the shared cache read by
        `is_episode_downloaded`. Runs on a schedule so show-lookup endpoints
        never scan the filesystem themselves.
        """
        rows = await self.tv_repository.get_episode_scan_rows()
        episode_ids_with_files = await self.tv_repository.get_episode_ids_with_files()
        statuses = await asyncio.to_thread(
            self._scan_downloaded_episodes, rows, episode_ids_with_files
        )
        set_cached_downloaded_statuses(DownloadedMediaType.episode, statuses)

    def _scan_downloaded_episodes(
        self,
        rows: Sequence[tuple[ShowId, str, str | None, int, EpisodeId, int]],
        episode_ids_with_files: set[EpisodeId],
    ) -> dict[EpisodeId, bool]:
        video_extensions = {".mkv", ".mp4", ".avi", ".mov"}
        statuses: dict[EpisodeId, bool] = {}
        season_filenames_by_key: dict[tuple[ShowId, int], list[str]] = {}

        for (
            show_id,
            show_directory_name,
            show_library,
            season_number,
            episode_id,
            episode_number,
        ) in rows:
            if episode_id not in episode_ids_with_files:
                statuses[episode_id] = False
                continue

            season_key = (show_id, season_number)
            filenames = season_filenames_by_key.get(season_key)
            if filenames is None:
                misc_config = get_config().misc
                show_dir = self.get_root_directory(
                    media=SimpleNamespace(
                        directory_name=show_directory_name, library=show_library
                    ),
                    default_dir=misc_config.tv_directory,
                    libraries=misc_config.tv_libraries,
                )
                season_dir = show_dir / season_directory_name(season_number)
                try:
                    filenames = (
                        [f.name.lower() for f in season_dir.iterdir() if f.is_file()]
                        if season_dir.exists()
                        else []
                    )
                except OSError as e:
                    log.error(f"Disk check failed for season directory {season_dir}: {e}")
                    filenames = []
                season_filenames_by_key[season_key] = filenames

            episode_token = f"s{season_number:02d}e{episode_number:02d}"
            statuses[episode_id] = any(
                episode_token in name and Path(name).suffix in video_extensions
                for name in filenames
            )

        return statuses

    async def episode_file_exists_on_file(self, episode_file: EpisodeFile) -> bool:
        """
        Check if an episode file exists on the filesystem.

        :param episode_file: The episode file to check.
        :return: True if the file exists, False otherwise.
        """
        return await self.media_file_is_imported(media_file=episode_file)

    async def get_show_by_external_id(
        self, external_id: int, metadata_provider: str
    ) -> Show | None:
        """
        Get a show by its external ID and metadata provider.

        :param external_id: The external ID of the show.
        :param metadata_provider: The metadata provider.
        :return: The show or None if not found.
        """
        return await self.tv_repository.get_show_by_external_id(
            external_id=external_id, metadata_provider=metadata_provider
        )

    async def get_season(self, season_id: SeasonId) -> Season:
        """
        Get a season by its ID.

        :param season_id: The ID of the season.
        :return: The season.
        """
        season = await self.tv_repository.get_season(season_id=season_id)
        return await self.attach_media_images(season)

    async def get_episode(self, episode_id: EpisodeId) -> Episode:
        """
        Get an episode by its ID.

        :param episode_id: The ID of the episode.
        :return: The episode.
        """
        return await self.tv_repository.get_episode(episode_id=episode_id)

    async def get_season_by_episode(self, episode_id: EpisodeId) -> Season:
        """
        Get a season by the episode ID.

        :param episode_id: The ID of the episode.
        :return: The season.
        """
        return await self.tv_repository.get_season_by_episode(episode_id=episode_id)

    async def get_torrents_for_show(self, show: Show) -> RichShowTorrent:
        """
        Get torrents for a given show.

        :param show: The show.
        :return: A rich show torrent.
        """
        show_torrents = await self.tv_repository.get_torrents_by_show_id(show_id=show.id)
        rich_season_torrents = []
        for show_torrent in show_torrents:
            seasons = await self.tv_repository.get_seasons_by_torrent_id(
                torrent_id=show_torrent.id
            )
            episodes = await self.tv_repository.get_episodes_by_torrent_id(
                torrent_id=show_torrent.id
            )
            episode_files = await self.torrent_service.get_episode_files_of_torrent(
                torrent=show_torrent
            )

            file_path_suffix = (
                episode_files[0].file_path_suffix if episode_files else ""
            )
            season_torrent = RichSeasonTorrent(
                torrent_id=show_torrent.id,
                torrent_title=show_torrent.title,
                status=show_torrent.status,
                quality=show_torrent.quality,
                imported=show_torrent.imported,
                seasons=seasons,
                episodes=episodes if len(seasons) == 1 else [],
                file_path_suffix=file_path_suffix,
                usenet=show_torrent.usenet,
            )
            rich_season_torrents.append(season_torrent)

        return RichShowTorrent(
            show_id=show.id,
            name=show.name,
            slug=show.slug,
            year=show.year,
            metadata_provider=show.metadata_provider,
            torrents=rich_season_torrents,
        )

    async def get_all_shows_with_torrents(self) -> list[RichShowTorrent]:
        """
        Get all shows with torrents.

        :return: A list of rich show torrents.
        """
        shows = await self.tv_repository.get_all_shows_with_torrents()
        return [await self.get_torrents_for_show(show=show) for show in shows]

    async def download_torrent(
        self,
        public_indexer_result_id: IndexerQueryResultId,
        show_id: ShowId,
        override_show_file_path_suffix: str = "",
        user_id: UUID | None = None,
    ) -> Torrent:
        """
        Download a torrent for a given indexer result and show.

        :param public_indexer_result_id: The ID of the indexer result.
        :param show_id: The ID of the show.
        :param override_show_file_path_suffix: Optional override for the file path suffix.
        :param user_id: If given, the user that triggered the download, recorded on
            the torrent as its initiator.
        :return: The downloaded torrent.
        """
        indexer_result = await self.indexer_service.get_result(
            result_id=public_indexer_result_id
        )
        show_torrent = await self.torrent_service.download(
            indexer_result=indexer_result, user_id=user_id
        )
        await self.torrent_service.pause_download(torrent=show_torrent)

        try:
            for season_number in indexer_result.season:
                season = await self.tv_repository.get_season_by_number(
                    season_number=season_number, show_id=show_id
                )
                episodes = {episode.number: episode.id for episode in season.episodes}

                if indexer_result.episode:
                    episode_ids = []
                    missing_episodes = []
                    for ep_number in indexer_result.episode:
                        ep_id = episodes.get(EpisodeNumber(ep_number))
                        if ep_id is None:
                            missing_episodes.append(ep_number)
                            continue
                        episode_ids.append(ep_id)
                    if missing_episodes:
                        log.warning(
                            "Some episodes from indexer result were not found in season %s "
                            "for show %s and will be skipped: %s",
                            season.id,
                            show_id,
                            ", ".join(str(ep) for ep in missing_episodes),
                        )
                else:
                    episode_ids = [episode.id for episode in season.episodes]

                for episode_id in episode_ids:
                    episode_file = EpisodeFile(
                        episode_id=episode_id,
                        quality=indexer_result.quality,
                        torrent_id=show_torrent.id,
                        file_path_suffix=override_show_file_path_suffix,
                    )
                    await self.tv_repository.add_episode_file(episode_file=episode_file)

        except IntegrityError:
            log.error(
                f"Episode file for episode {episode_id} of season {season.id} and quality {indexer_result.quality} already exists, skipping."
            )
            await self.tv_repository.remove_episode_files_by_torrent_id(show_torrent.id)
            await self.torrent_service.cancel_download(
                torrent=show_torrent, delete_files=True
            )
            raise
        else:
            log.info(
                f"Successfully added episode files for torrent {show_torrent.title} and show ID {show_id}"
            )
            await self.torrent_service.resume_download(torrent=show_torrent)

        return show_torrent

    def get_root_show_directory(self, show: ShowSummary) -> Path:
        misc_config = get_config().misc
        return self.get_root_directory(
            media=show,
            default_dir=misc_config.tv_directory,
            libraries=misc_config.tv_libraries,
        )

    async def set_show_continuous_download(
        self, show: Show, continuous_download: bool
    ) -> Show:
        """
        Set the continuous download flag for a show.

        :param show: The show object.
        :param continuous_download: True to enable continuous download, False to disable.
        :return: The updated Show object.
        """
        return await self.tv_repository.update_show_attributes(
            show_id=show.id, continuous_download=continuous_download
        )

    async def import_all_torrents(self) -> None:
        """
        Delegate to TvImportService.
        """
        await self.tv_import_service.import_all_torrents()

    async def update_all_non_ended_shows_metadata(self) -> None:
        """
        Delegate to TvMetadataService.
        """
        await self.tv_metadata_service.update_all_non_ended_shows_metadata()
