import asyncio
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path

from media_manager.common.import_scan_cache import (
    ImportScanMediaType,
    set_cached_importable_media,
)
from media_manager.common.service import BaseMediaService
from media_manager.config import MediaManagerConfig
from media_manager.exceptions import BadRequestError, ConflictError
from media_manager.metadataProvider.abstract_metadata_provider import (
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.dependencies import get_metadata_provider
from media_manager.movies.metadata import MovieMetadataService
from media_manager.movies.repository import MovieRepository
from media_manager.movies.schemas import Movie, MovieFile
from media_manager.notification.service import NotificationService
from media_manager.schemas import MediaImportSuggestion
from media_manager.torrent.schemas import ImportErrorKind, Quality, Torrent
from media_manager.torrent.service import TorrentService
from media_manager.torrent.utils import (
    get_files_for_import,
    get_torrent_filepath,
    import_file,
    list_torrent_media_files,
    remove_special_characters,
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
        misc_config = MediaManagerConfig().misc
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
    ) -> bool:
        if not video_files and not subtitle_files:
            log.error(f"No video or subtitle files found for movie {movie.name}")
            return False

        movie_file_name = f"{remove_special_characters(movie.name)} ({movie.year})"
        movie_root_path = self.get_media_root_path(media=movie)
        if file_path_suffix:
            movie_file_name += f" - {file_path_suffix}"

        imported_any = False
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
            return False
        else:
            return imported_any

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

        success = [
            await self.import_movie(
                movie, video_files, subtitle_files, mf.file_path_suffix
            )
            for mf in movie_files
        ]

        if all(success):
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

    async def get_import_candidates(
        self, movie_path: Path, metadata_provider: AbstractMetadataProvider
    ) -> MediaImportSuggestion:
        return await super().get_import_candidates(
            directory=movie_path,
            metadata_provider=metadata_provider,
            search_func=self.movie_metadata_service.search_for_movie,
        )

    async def import_existing_movie(self, movie: Movie, source_directory: Path) -> bool:
        async def _logic(
            m: Movie, path: Path, add_cb: Callable[[MovieFile], Awaitable[None]]
        ) -> bool:
            v, s, _ = await asyncio.to_thread(get_files_for_import, directory=path)
            res = await self.import_movie(m, v, s, "IMPORTED")
            if res:
                await add_cb(
                    MovieFile(
                        movie_id=m.id,
                        file_path_suffix="IMPORTED",
                        torrent_id=None,
                        quality=Quality.unknown,
                    )
                )
            return res

        return await self.import_existing_media(
            media=movie,
            source_directory=source_directory,
            import_func=_logic,
            add_file_record_func=self.movie_repository.add_movie_file,
        )

    async def get_importable_movies(
        self, metadata_provider: AbstractMetadataProvider
    ) -> list[MediaImportSuggestion]:
        return await self.get_importable_media(
            root_path=MediaManagerConfig().misc.movie_directory,
            metadata_provider=metadata_provider,
            get_candidates_func=self.get_import_candidates,
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
