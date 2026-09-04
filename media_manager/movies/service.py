import asyncio
import logging
import shutil
from pathlib import Path
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
    movie_file_stem,
)
from media_manager.common.service import BaseMediaService
from media_manager.config import get_config
from media_manager.indexer.schemas import IndexerQueryResult, IndexerQueryResultId
from media_manager.indexer.scoring import resolve_slot_label, slot_and_score_results
from media_manager.indexer.service import IndexerService
from media_manager.movies.importer import MovieImportService
from media_manager.movies.metadata import MovieMetadataService
from media_manager.movies.repository import MovieRepository
from media_manager.movies.schemas import (
    Movie,
    MovieFile,
    MovieId,
    MovieListItem,
    PublicMovie,
    PublicMovieFile,
    RichMovieTorrent,
)
from media_manager.notification.service import NotificationService
from media_manager.torrent.schemas import (
    Quality,
    QualityStrings,
    Torrent,
)
from media_manager.torrent.service import TorrentService
from media_manager.torrent.utils import remove_special_characters

log = logging.getLogger(__name__)


class MovieService(BaseMediaService[Movie, Movie]):
    def __init__(
        self,
        movie_repository: MovieRepository,
        torrent_service: TorrentService,
        indexer_service: IndexerService,
        notification_service: NotificationService,
        movie_import_service: MovieImportService,
        movie_metadata_service: MovieMetadataService,
    ) -> None:
        super().__init__(
            repository=movie_repository,
            torrent_service=torrent_service,
            indexer_service=indexer_service,
            notification_service=notification_service,
        )
        self.movie_repository = movie_repository
        self.movie_import_service = movie_import_service
        self.movie_metadata_service = movie_metadata_service

    async def delete_movie(
        self,
        movie: Movie,
        delete_files_on_disk: bool = False,
        delete_torrents: bool = False,
    ) -> None:
        """
        Delete a movie from the database, optionally deleting files and torrents.

        :param movie: The movie to delete.
        :param delete_files_on_disk: Whether to delete the movie's files from disk.
        :param delete_torrents: Whether to delete associated torrents from the torrent client.
        """
        if delete_files_on_disk or delete_torrents:
            if delete_files_on_disk:
                # Get the movie's directory path
                movie_dir = self.get_movie_root_path(movie=movie)

                if movie_dir.exists() and movie_dir.is_dir():
                    try:
                        await asyncio.to_thread(shutil.rmtree, movie_dir)
                        log.info(f"Deleted movie directory: {movie_dir}")
                    except OSError:
                        log.exception(f"Deleting movie directory: {movie_dir}")

            if delete_torrents:
                # Get all torrents associated with this movie
                movie_torrents = await self.movie_repository.get_torrents_by_movie_id(
                    movie_id=movie.id
                )

                for movie_torrent in movie_torrents:
                    torrent = await self.torrent_service.get_torrent_by_id(
                        torrent_id=movie_torrent.torrent_id
                    )
                    try:
                        await self.torrent_service.cancel_download(
                            torrent=torrent, delete_files=True
                        )
                        log.info(f"Deleted torrent: {torrent.torrent_title}")
                    except Exception:
                        log.exception(f"Failed to delete torrent {torrent.hash}")

        # Delete from database
        await self.movie_repository.delete_movie(movie.id)

    async def get_public_movie_files(self, movie: Movie) -> list[PublicMovieFile]:
        """
        Get all public movie files for a given movie, enriched with their
        resolved path on disk and the details probed from the file itself.

        :param movie: The movie object.
        :return: A list of public movie files.
        """
        movie_files = await self.movie_repository.get_movie_files_by_movie_id(
            movie_id=movie.id
        )
        public_movie_files = [PublicMovieFile.model_validate(x) for x in movie_files]
        for movie_file in public_movie_files:
            imported = await self.movie_file_exists_on_file(movie_file=movie_file)
            movie_file.imported = imported
            movie_file.downloaded = imported

        await attach_media_file_details(
            public_movie_files,
            [
                self.get_movie_file_location(movie=movie, movie_file=movie_file)
                for movie_file in public_movie_files
            ],
        )
        return public_movie_files

    def get_movie_file_location(
        self, movie: Movie, movie_file: MovieFile
    ) -> MediaFileLocation:
        """
        Where a movie file is expected on disk: directly inside the movie's
        own directory, named after the movie, reported relative to the parent
        movies folder (the default movie directory, or the movie's library
        root if it belongs to one).
        """
        movie_root_path = self.get_movie_root_path(movie=movie)
        return MediaFileLocation(
            directory=movie_root_path,
            stem=movie_file_stem(
                movie_name=movie.name,
                year=movie.year,
                file_path_suffix=movie_file.file_path_suffix,
            ),
            relative_to=movie_root_path.parent,
            media_root=movie_root_path,
        )

    async def scan_library_files(self) -> LibraryScanCounts:
        """
        Reconcile every movie's file records with the files on disk: relink
        records that lost track of their file, clear the path of records whose
        file is gone, and adopt video files sitting anywhere under a movie's
        directory without a record of their own.

        Movies whose root directory does not exist are skipped untouched - a
        library that isn't mounted must not be mistaken for a library that
        emptied itself.

        :return: What the scan changed.
        """
        movies = await self.movie_repository.get_movies()
        files_by_movie = (
            await self.movie_repository.get_all_movie_files_grouped_by_movie()
        )
        plans = await scan_media_targets(
            [
                self.movie_import_service.build_scan_target(
                    movie=movie, movie_files=files_by_movie.get(movie.id, [])
                )
                for movie in movies
            ]
        )
        for movie, plan in zip(movies, plans, strict=True):
            await self.movie_import_service.apply_scan_plan(movie=movie, plan=plan)

        counts = count_plans(plans)
        log.info(
            f"Movie library scan: {counts.items_scanned} scanned, "
            f"{counts.items_skipped} skipped (directory missing), "
            f"{counts.paths_relinked} paths relinked, "
            f"{counts.paths_cleared} paths cleared, "
            f"{counts.files_adopted} files adopted"
        )
        return counts

    async def get_all_available_torrents_for_movie(
        self,
        movie: Movie,
        search_query_override: str | None = None,
        allow_language_variants: list[str] | None = None,
    ) -> list[IndexerQueryResult]:
        """
        Get all available torrents for a given movie.

        :param movie: The movie object.
        :param search_query_override: Optional override for the search query.
        :param allow_language_variants: Language variants (e.g. "multi",
            "dubbed") to allow for this search on top of the configured
            defaults.
        :return: A list of indexer query results.
        """
        if search_query_override:
            return await self.indexer_service.search(query=search_query_override, is_tv=False)

        torrents = await self.indexer_service.search_movie(movie=movie)

        return slot_and_score_results(
            is_tv=False,
            results=torrents,
            media=movie,
            allow_language_variants=allow_language_variants,
        )

    async def get_public_movie_by_id(self, movie: Movie) -> PublicMovie:
        """
        Get a public movie from a Movie object.

        :param movie: The movie object.
        :return: A public movie.
        """
        torrents = (await self.get_torrents_for_movie(movie=movie)).torrents
        public_movie = PublicMovie.model_validate(movie)
        public_movie.downloaded = await self.is_movie_downloaded(movie_id=movie.id)
        public_movie.torrents = torrents
        return await self.attach_media_images(public_movie)

    async def get_movie_by_id(self, movie_id: MovieId) -> Movie:
        """
        Get a movie by its ID.

        :param movie_id: The ID of the movie.
        :return: The movie.
        """
        return await self.movie_repository.get_movie_by_id(movie_id)

    async def get_movie_by_slug(self, slug: str) -> Movie:
        """
        Get a movie by its slug.

        :param slug: The slug of the movie.
        :return: The movie.
        """
        return await self.movie_repository.get_movie_by_slug(slug)

    async def is_movie_downloaded(self, movie_id: MovieId) -> bool:
        """
        Check if a movie is downloaded.

        Reads the shared cache populated by the periodic
        `rescan_downloaded_movies` scan, so this never queries the torrent
        for every movie file on the request path. If the scan hasn't run
        yet (e.g. briefly after startup), falls back to querying directly.

        :param movie_id: The ID of the movie.
        :return: True if the movie is downloaded, False otherwise.
        """
        cached = get_cached_downloaded(DownloadedMediaType.movie, movie_id)
        if cached is not None:
            return cached

        movie_files = await self.movie_repository.get_movie_files_by_movie_id(
            movie_id=movie_id
        )
        for movie_file in movie_files:
            if await self.movie_file_exists_on_file(movie_file=movie_file):
                return True
        return False

    async def rescan_downloaded_movies(self) -> None:
        """
        Recompute which movies are downloaded and refresh the shared cache
        read by `is_movie_downloaded`. Runs on a schedule so movie-lookup
        endpoints never recheck every movie file's torrent status
        themselves.
        """
        statuses = await self.movie_repository.get_movie_downloaded_statuses()
        set_cached_downloaded_statuses(DownloadedMediaType.movie, statuses)

    async def movie_file_exists_on_file(self, movie_file: MovieFile) -> bool:
        """
        Check if a movie file exists on the filesystem.

        :param movie_file: The movie file to check.
        :return: True if the file exists, False otherwise.
        """
        return await self.media_file_is_imported(media_file=movie_file)

    async def get_movie_by_external_id(
        self, external_id: int, metadata_provider: str
    ) -> Movie | None:
        """
        Get a movie by its external ID and metadata provider.

        :param external_id: The external ID of the movie.
        :param metadata_provider: The metadata provider.
        :return: The movie or None if not found.
        """
        return await self.movie_repository.get_movie_by_external_id(
            external_id=external_id, metadata_provider=metadata_provider
        )

    async def set_movie_library(self, movie: Movie, library: str) -> None:
        await self.movie_repository.set_movie_library(movie.id, library)

    async def get_all_movies(self) -> list[MovieListItem]:
        """
        Get all movies in the library, with the downloaded/quality fields the
        library page's filters need.
        """
        movies = await self.attach_media_images_many(await self.get_all_media())
        download_info = await self.movie_repository.get_movie_download_info()
        list_items = []
        for movie in movies:
            downloaded, quality = download_info.get(movie.id, (False, None))
            list_items.append(
                MovieListItem(
                    **movie.model_dump(), downloaded=downloaded, quality=quality
                )
            )
        return list_items

    async def get_torrents_for_movie(self, movie: Movie) -> RichMovieTorrent:
        """
        Get torrents for a given movie.

        :param movie: The movie.
        :return: A rich movie torrent.
        """
        movie_torrents = await self.movie_repository.get_torrents_by_movie_id(
            movie_id=movie.id
        )
        return RichMovieTorrent(
            movie_id=movie.id,
            name=movie.name,
            slug=movie.slug,
            year=movie.year,
            metadata_provider=movie.metadata_provider,
            torrents=movie_torrents,
        )

    async def get_all_movies_with_torrents(self) -> list[RichMovieTorrent]:
        """
        Get all movies with torrents.

        :return: A list of rich movie torrents.
        """
        movies = await self.movie_repository.get_all_movies_with_torrents()
        return [await self.get_torrents_for_movie(movie=movie) for movie in movies]

    async def download_torrent(
        self,
        public_indexer_result_id: IndexerQueryResultId,
        movie: Movie,
        override_movie_file_path_suffix: str = "",
        user_id: UUID | None = None,
    ) -> Torrent:
        """
        Download a torrent for a given indexer result and movie.

        :param public_indexer_result_id: The ID of the indexer result.
        :param movie: The movie object.
        :param override_movie_file_path_suffix: Optional override for the file path suffix.
        :param user_id: If given, the user that triggered the download, recorded on
            the torrent as its initiator.
        :return: The downloaded torrent.
        """
        indexer_result = await self.indexer_service.get_result(
            result_id=public_indexer_result_id
        )
        file_path_suffix = override_movie_file_path_suffix or self._default_file_path_suffix(
            indexer_result
        )
        movie_torrent = await self.torrent_service.download(
            indexer_result=indexer_result, user_id=user_id
        )
        await self.torrent_service.pause_download(torrent=movie_torrent)
        movie_file = MovieFile(
            movie_id=movie.id,
            quality=indexer_result.quality,
            torrent_id=movie_torrent.id,
            file_path_suffix=file_path_suffix,
        )
        try:
            await self.movie_repository.add_movie_file(movie_file=movie_file)
        except IntegrityError:
            log.warning(
                f"Movie file for movie {movie.name} and torrent {movie_torrent.title} already exists"
            )
            await self.torrent_service.cancel_download(
                torrent=movie_torrent, delete_files=True
            )
            raise
        else:
            log.info(
                f"Added movie file for movie {movie.name} and torrent {movie_torrent.title}"
            )
            await self.torrent_service.resume_download(torrent=movie_torrent)
        return movie_torrent

    @staticmethod
    def _default_file_path_suffix(indexer_result: IndexerQueryResult) -> str:
        """
        Default file path suffix for a download that didn't get an explicit
        override: the label of the slot the release's stored attributes
        match (e.g. "1080p Encode", "4K Remux"), falling back to a coarse
        quality string if it didn't match a configured slot. Sanitized since
        it ends up as part of a filename on disk.
        """
        label = resolve_slot_label(indexer_result)
        if not label and indexer_result.quality != Quality.unknown:
            label = QualityStrings[indexer_result.quality.name].value
        return remove_special_characters(label) if label else ""

    def get_movie_root_path(self, movie: Movie) -> Path:
        misc_config = get_config().misc
        return self.get_root_directory(
            media=movie,
            default_dir=misc_config.movie_directory,
            libraries=misc_config.movie_libraries,
        )

    async def import_all_torrents(self) -> None:
        """
        Delegate to MovieImportService.
        """
        await self.movie_import_service.import_all_torrents()

    async def update_all_metadata(self) -> None:
        """
        Delegate to MovieMetadataService.
        """
        await self.movie_metadata_service.update_all_metadata()
