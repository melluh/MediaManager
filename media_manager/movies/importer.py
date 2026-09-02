import asyncio
import logging
import re
from collections.abc import Sequence
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
from media_manager.common.media_files import movie_file_stem
from media_manager.common.service import BaseMediaService
from media_manager.config import MediaManagerConfig, get_config
from media_manager.exceptions import BadRequestError, ConflictError
from media_manager.metadataProvider.abstract_metadata_provider import (
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.dependencies import get_metadata_provider
from media_manager.metadataProvider.schemas import (
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.metadata import MovieMetadataService
from media_manager.movies.repository import MovieRepository
from media_manager.movies.schemas import Movie, MovieFile
from media_manager.notification.service import NotificationService
from media_manager.schemas import MediaImportSuggestion
from media_manager.torrent.schemas import ImportErrorKind, Torrent
from media_manager.torrent.service import TorrentService
from media_manager.torrent.utils import (
    get_files_for_import,
    get_torrent_filepath,
    import_file,
    list_torrent_media_files,
)

log = logging.getLogger(__name__)


class MovieImportService(BaseMediaService[Movie, Movie]):
    def __init__(
        self,
        movie_repository: MovieRepository,
        torrent_service: TorrentService,
        notification_service: NotificationService,
        movie_metadata_service: MovieMetadataService,
    ) -> None:
        super().__init__(
            repository=movie_repository,
            torrent_service=torrent_service,
            indexer_service=None,  # type: ignore[arg-type]
            notification_service=notification_service,
        )
        self.movie_repository = movie_repository
        self.movie_metadata_service = movie_metadata_service

    def get_media_root_path(self, media: Movie) -> Path:
        # Cached: a library-wide scan resolves one root per media item, and
        # re-parsing config.toml for each of them is pure waste.
        misc_config = get_config().misc
        return self.get_root_directory(
            media=media,
            default_dir=misc_config.movie_directory,
            libraries=misc_config.movie_libraries,
        )

    async def import_movie(
        self,
        movie: Movie,
        video_files: list[Path],
        subtitle_files: list[Path],
        file_path_suffix: str = "",
    ) -> tuple[bool, str | None]:
        """
        Imports a movie's files into its root directory.

        :return: Whether anything was imported, and the video file's path
            relative to the movie's root directory (None when only subtitles
            were imported).
        """
        if not video_files and not subtitle_files:
            log.error(f"No video or subtitle files found for movie {movie.name}")
            return False, None

        movie_file_name = movie_file_stem(
            movie_name=movie.name,
            year=movie.year,
            file_path_suffix=file_path_suffix,
        )
        movie_root_path = self.get_media_root_path(media=movie)

        imported_any = False
        video_relative_path: str | None = None
        try:
            movie_root_path.mkdir(parents=True, exist_ok=True)
            if video_files:
                target_video_file = (
                    movie_root_path / f"{movie_file_name}{video_files[0].suffix}"
                )
                await asyncio.to_thread(
                    import_file,
                    target_file=target_video_file,
                    source_file=video_files[0],
                )
                imported_any = True
                video_relative_path = target_video_file.name

            for subtitle_file in subtitle_files:
                match = re.search(
                    r"[. ]([a-z]{2})\.srt$", subtitle_file.name, re.IGNORECASE
                )
                if match:
                    lang = match.group(1)
                    target = movie_root_path / f"{movie_file_name}.{lang}.srt"
                    await asyncio.to_thread(
                        import_file, target_file=target, source_file=subtitle_file
                    )
                    imported_any = True
        except Exception:
            log.exception(f"Failed to import movie {movie.name}")
            return False, None
        else:
            return imported_any, video_relative_path

    async def import_torrent_files(self, torrent: Torrent, movie: Movie) -> None:
        # Filesystem scan + archive extraction; offload off the event loop.
        video_files, subtitle_files, _ = await asyncio.to_thread(
            get_files_for_import, torrent=torrent
        )
        if len(video_files) == 0:
            await self.notify_import_failure(
                torrent,
                movie.name,
                "movie",
                "No video files found."
            )
            return

        if len(video_files) != 1:
            await self.notify_import_failure(
                torrent,
                movie.name,
                "movie",
                "Multiple video files found. Manual import required.",
                import_error_kind=ImportErrorKind.multiple_video_files,
            )
            return

        await self._import_resolved_files(torrent, movie, video_files, subtitle_files)

    async def resolve_multiple_video_files(
        self, torrent: Torrent, movie: Movie, relative_path: str
    ) -> bool:
        """
        Manually resolves a torrent that failed automatic import because it
        contained multiple video files, by importing the one the caller
        picked.

        :param relative_path: Path of the chosen file, relative to the
            torrent's download directory, exactly as returned by
            `TorrentService.get_import_candidates`.
        """
        if torrent.import_error_kind != ImportErrorKind.multiple_video_files:
            msg = "This torrent has no pending multiple-video-file import to resolve."
            raise ConflictError(msg)

        torrent_dir = get_torrent_filepath(torrent=torrent)
        # Re-scan rather than trust the caller's path outright: only a file
        # that's actually present now is a valid import target.
        video_files, subtitle_files = await asyncio.to_thread(
            list_torrent_media_files, torrent=torrent
        )
        selected_file = next(
            (
                file
                for file in video_files
                if file.relative_to(torrent_dir).as_posix() == relative_path
            ),
            None,
        )
        if selected_file is None:
            msg = f"'{relative_path}' is not one of the video files found for this torrent."
            raise BadRequestError(msg)

        return await self._import_resolved_files(
            torrent, movie, [selected_file], subtitle_files
        )

    async def _import_resolved_files(
        self,
        torrent: Torrent,
        movie: Movie,
        video_files: list[Path],
        subtitle_files: list[Path],
    ) -> bool:
        # A failed attempt must not clear a recognized failure kind - otherwise
        # a transient error on manual resolution would permanently lock the
        # torrent out of the resolution flow that gated this call.
        kind_on_failure = torrent.import_error_kind

        movie_files = await self.torrent_service.get_movie_files_of_torrent(
            torrent=torrent
        )
        if not movie_files:
            await self.notify_import_failure(
                torrent, movie.name, "movie", import_error_kind=kind_on_failure
            )
            return False

        imported_all = True
        for movie_file in movie_files:
            imported, relative_path = await self.import_movie(
                movie, video_files, subtitle_files, movie_file.file_path_suffix
            )
            imported_all = imported_all and imported
            # The file record was created when the download started, so where
            # the file ended up is only known now.
            if relative_path:
                await self.movie_repository.set_movie_file_relative_path(
                    movie_id=movie.id,
                    file_path_suffix=movie_file.file_path_suffix,
                    relative_path=relative_path,
                )

        if imported_all:
            torrent.imported = True
            torrent.import_error = None
            torrent.import_error_kind = None
            await self.torrent_service.torrent_repository.save_torrent(torrent=torrent)
            await self.notify_import_success(movie.name, "movie")
            return True

        await self.notify_import_failure(
            torrent, movie.name, "movie", import_error_kind=kind_on_failure
        )
        return False

    async def get_import_suggestion(
        self, movie_path: Path, metadata_provider: AbstractMetadataProvider
    ) -> MediaImportSuggestion:
        return await super().get_import_suggestion(
            directory=movie_path,
            metadata_provider=metadata_provider,
            search_func=self.movie_metadata_service.search_for_movie,
            get_metadata_func=metadata_provider.get_movie_metadata,
            get_images_func=metadata_provider.get_movie_images,
            media_type=MediaType.movie,
        )

    async def get_import_candidates(
        self, movie_path: Path, metadata_provider: AbstractMetadataProvider
    ) -> list[MetaDataProviderSearchResult]:
        return await super().get_import_candidates(
            directory=movie_path,
            metadata_provider=metadata_provider,
            search_func=self.movie_metadata_service.search_for_movie,
        )

    def build_scan_target(
        self, movie: Movie, movie_files: Sequence[MovieFile]
    ) -> ScanTarget:
        """
        The scan target for one movie, shared by the library-wide scan and by
        the single-movie scan an import runs.

        :param movie: The movie to scan.
        :param movie_files: The movie's existing file records.
        :return: The target describing what to look for and what is on record.
        """
        movie_root = self.get_media_root_path(media=movie)
        canonical_stem = movie_file_stem(movie_name=movie.name, year=movie.year)

        def adopt(_path: Path) -> AdoptionOwner:
            # Every video file under a movie's own directory is a file of that
            # movie; there is nothing else it could belong to.
            return AdoptionOwner(key=movie.id, canonical_stem=canonical_stem)

        return ScanTarget(
            media_root=movie_root,
            records=[
                ScanRecord(
                    owner_key=movie.id,
                    stem=movie_file_stem(
                        movie_name=movie.name,
                        year=movie.year,
                        file_path_suffix=movie_file.file_path_suffix,
                    ),
                    file_path_suffix=movie_file.file_path_suffix,
                    relative_path=movie_file.relative_path,
                )
                for movie_file in movie_files
            ],
            adopt=adopt,
        )

    async def apply_scan_plan(self, movie: Movie, plan: MediaScanPlan) -> None:
        """
        Writes what a scan decided for one movie.

        :param movie: The scanned movie.
        :param plan: The changes the scan planned for it.
        """
        for path_update in [*plan.relinked, *plan.cleared]:
            await self.movie_repository.set_movie_file_relative_path(
                movie_id=movie.id,
                file_path_suffix=path_update.record.file_path_suffix,
                relative_path=path_update.relative_path,
            )
        for adoption in plan.adoptions:
            await self.movie_repository.add_movie_file(
                movie_file=MovieFile(
                    movie_id=movie.id,
                    quality=adoption.quality,
                    torrent_id=None,
                    file_path_suffix=adoption.file_path_suffix,
                    relative_path=adoption.relative_path,
                )
            )

    async def scan_movie_files(self, movie: Movie) -> MediaScanPlan:
        """
        Scans a single movie's directory and applies what it finds.

        :param movie: The movie to scan.
        :return: The changes that were applied.
        """
        movie_files = await self.movie_repository.get_movie_files_by_movie_id(
            movie_id=movie.id
        )
        target = self.build_scan_target(movie=movie, movie_files=movie_files)
        plan = (await scan_media_targets([target]))[0]
        await self.apply_scan_plan(movie=movie, plan=plan)
        return plan

    async def import_existing_movie(self, movie: Movie, source_directory: Path) -> bool:
        """
        Adopts a movie that is already on disk, without moving a single file:
        the movie is pointed at the directory the user already has, and a scan
        of that directory records the files in it.

        :param movie: The movie to attach the existing directory to.
        :param source_directory: The directory the movie's files are in.
        :return: Whether any file was adopted.
        :raises ConflictError: If the movie already has file records, which
            re-pointing its directory would orphan, or if the directory does
            not sit in the library the movie is assigned to.
        """
        existing_files = await self.movie_repository.get_movie_files_by_movie_id(
            movie_id=movie.id
        )
        if existing_files:
            msg = (
                f"{movie.name} already has files in the library; "
                "importing an existing directory would orphan them."
            )
            raise ConflictError(msg)

        # The parent of a media item's directory comes from its library, while
        # the import source always sits in the default root. If those disagree
        # the scan would look in a directory that does not exist, so refuse
        # before storing a directory name that points nowhere.
        expected_root = self.get_media_root_path(
            media=movie.model_copy(update={"directory_name": source_directory.name})
        )
        if expected_root != source_directory:
            msg = (
                f"{movie.name} is assigned to the '{movie.library}' library, "
                f"which does not contain {source_directory}. Move the directory "
                f"into that library, or reassign the movie to the default library."
            )
            raise ConflictError(msg)

        await self.movie_repository.set_directory_name(
            entity_id=movie.id, directory_name=source_directory.name
        )
        # The scan resolves the movie's root from its directory name, so it has
        # to see the name that was just stored rather than the stale one.
        movie = movie.model_copy(update={"directory_name": source_directory.name})

        plan = await self.scan_movie_files(movie=movie)
        if plan.adoptions:
            log.info(
                f"Imported {movie.name} in place from {source_directory}: "
                f"{len(plan.adoptions)} file(s) adopted"
            )
            # The directory now belongs to a media item, so the scan will skip
            # it from here on and its cached match is dead weight.
            await asyncio.to_thread(delete_import_sidecar, source_directory)
        return bool(plan.adoptions)

    async def get_importable_movies(
        self, metadata_provider: AbstractMetadataProvider
    ) -> list[MediaImportSuggestion]:
        return await self.get_importable_media(
            root_path=MediaManagerConfig().misc.movie_directory,
            metadata_provider=metadata_provider,
            get_suggestion_func=self.get_import_suggestion,
        )

    async def rescan_importable_movies(self) -> list[MediaImportSuggestion]:
        """
        Re-scans the movie directory for importable movies and refreshes the
        cache read by the `/importable` endpoint. Always scans with the
        default (tmdb) metadata provider, matching what the frontend requests.
        """
        suggestions = await self.get_importable_movies(
            metadata_provider=get_metadata_provider()
        )
        set_cached_importable_media(ImportScanMediaType.movie, suggestions)
        return suggestions

    async def import_all_torrents(self) -> None:
        await self.import_all_torrents_base(
            get_media_func=self.torrent_service.get_movie_of_torrent,
            import_torrent_func=self.import_torrent_files,
            media_type_name="movie",
        )
