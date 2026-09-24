import asyncio
import logging
import shutil
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from media_manager.common.library_scan import (
    LibraryScanCounts,
    count_plans,
    scan_media_targets,
)
from media_manager.common.media_files import (
    best_quality,
    distinct_subtitle_languages,
    refresh_media_file_details,
)
from media_manager.common.service import BaseMediaService
from media_manager.config import get_config
from media_manager.exceptions import MediaAlreadyExistsError
from media_manager.indexer.schemas import IndexerQueryResult, IndexerQueryResultId
from media_manager.indexer.scoring import resolve_slot_label, slot_and_score_results
from media_manager.indexer.service import IndexerService
from media_manager.movies.importer import MovieImportService
from media_manager.movies.metadata import MovieMetadataService
from media_manager.movies.repository import MovieRepository
from media_manager.movies.schemas import (
    Movie,
    MovieId,
    MovieListItem,
    PublicMovie,
    PublicMovieFile,
    RichMovieTorrent,
)
from media_manager.notification.service import NotificationService
from media_manager.torrent.schemas import (
    Torrent,
    TorrentWithProgress,
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
                        log.info(f"Deleted torrent: {torrent.title}")
                    except Exception:
                        log.exception(f"Failed to delete torrent {torrent.hash}")

        # Delete from database
        await self.movie_repository.delete_movie(movie.id)

    async def get_public_movie_files(self, movie: Movie) -> list[PublicMovieFile]:
        """
        Get all files of a given movie, enriched with their resolved path on
        disk and the details probed from the file itself (re-probed only if
        the file changed since it was last probed).

        :param movie: The movie object.
        :return: A list of public movie files.
        """
        movie_files = await self.movie_repository.get_movie_files_by_movie_id(
            movie_id=movie.id
        )
        return await self.movie_import_service.refresh_movie_file_details(
            movie=movie, movie_files=movie_files
        )

    async def refresh_all_movie_file_details(self) -> None:
        """
        Bring every movie file's stored probe details up to date, so the movie
        list's quality and subtitle filters see new and changed files without
        anyone opening their movie first. Unchanged files cost only a stat.
        """
        movies = await self.movie_repository.get_movies()
        files_by_movie = (
            await self.movie_repository.get_all_movie_files_grouped_by_movie()
        )
        # One batch for the whole library: a single stat/listing thread and a
        # bounded pool of ffprobe subprocesses, instead of per movie.
        all_files = [
            (movie, PublicMovieFile.model_validate(movie_file))
            for movie in movies
            for movie_file in files_by_movie.get(movie.id, [])
        ]
        changed = await refresh_media_file_details(
            [movie_file for _, movie_file in all_files],
            [
                self.movie_import_service.get_movie_file_location(movie=movie)
                for movie, _ in all_files
            ],
        )
        await self.movie_repository.update_movie_file_details(changed)
        log.info(
            f"Movie file probe refresh: {len(all_files)} files, "
            f"{len(changed)} updated"
        )

    async def scan_library_files(self) -> LibraryScanCounts:
        """
        Reconcile every movie's file records with the files on disk: relink
        records that lost track of their file, remove records whose file is
        gone, and adopt video files sitting anywhere under a movie's
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
            f"{counts.files_removed} missing files removed, "
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
        statuses = await self.get_movie_downloaded_statuses(movie_ids=[movie.id])
        public_movie.downloaded = statuses[movie.id]
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

    async def get_movie_downloaded_statuses(
        self, movie_ids: Sequence[MovieId]
    ) -> dict[MovieId, bool]:
        """
        Whether each movie has at least one file in the library.

        :param movie_ids: The movies to check.
        :return: A status for every given movie id.
        """
        with_files = await self.movie_repository.get_movie_ids_with_files(
            movie_ids=list(movie_ids)
        )
        return {movie_id: movie_id in with_files for movie_id in movie_ids}

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
        Get all movies in the library, with the downloaded/quality/subtitle
        fields the library page's filters need - read from the files' stored
        probe details, so this never probes anything itself.
        """
        movies = await self.attach_media_images_many(await self.get_all_media())
        details_by_movie = await self.movie_repository.get_all_movie_file_details()
        list_items = []
        for movie in movies:
            file_details = details_by_movie.get(movie.id, [])
            list_items.append(
                MovieListItem(
                    **movie.model_dump(),
                    downloaded=bool(file_details),
                    quality=best_quality(file_details),
                    subtitle_languages=distinct_subtitle_languages(file_details),
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

    async def get_torrents_with_progress_for_movie(
        self, movie_id: MovieId
    ) -> list[TorrentWithProgress]:
        """
        Get every torrent belonging to this movie - any initiating user, any
        status - enriched with live download status/progress, for the movie
        detail page's torrent table.
        """
        torrents = await self.movie_repository.get_full_torrents_by_movie_id(
            movie_id=movie_id
        )
        return await self.torrent_service.enrich_torrents(torrents)

    async def get_all_movies_with_torrents(self) -> list[RichMovieTorrent]:
        """
        Get all movies with torrents.

        :return: A list of rich movie torrents.
        """
        movies = await self.movie_repository.get_all_movies_with_torrents()
        return [await self.get_torrents_for_movie(movie=movie) for movie in movies]

    async def _check_file_path_suffix_is_free(
        self, movie: Movie, file_path_suffix: str
    ) -> None:
        """
        Refuses a download whose file would land on a version of the movie
        that's already in the library, or already being downloaded. Not
        enforced by a DB constraint (it depends on the other download's
        torrent state), so two concurrent requests could still both pass.
        """
        taken = await self.movie_repository.get_taken_movie_file_path_suffixes(
            movie_id=movie.id
        )
        if file_path_suffix in taken:
            msg = (
                f"A file or pending download for movie {movie.name} with this "
                "file path suffix already exists, refusing to start download."
            )
            log.warning(msg)
            raise MediaAlreadyExistsError(msg)

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

        await self._check_file_path_suffix_is_free(
            movie=movie, file_path_suffix=file_path_suffix
        )

        movie_torrent = await self.torrent_service.download(
            indexer_result=indexer_result, user_id=user_id
        )
        try:
            await self.torrent_service.pause_download(torrent=movie_torrent)
            await self.movie_repository.add_movie_download(
                torrent_id=movie_torrent.id,
                movie_id=movie.id,
                file_path_suffix=file_path_suffix,
            )
        except IntegrityError:
            log.warning(
                f"Torrent {movie_torrent.title} is already linked to movie {movie.name}"
            )
            await self.torrent_service.cancel_download(
                torrent=movie_torrent, delete_files=True
            )
            raise
        except Exception:
            log.exception(
                f"Failed to link torrent {movie_torrent.title} to movie {movie.name}, cancelling download"
            )
            await self.torrent_service.cancel_download(
                torrent=movie_torrent, delete_files=True
            )
            raise
        else:
            log.info(
                f"Linked torrent {movie_torrent.title} to movie {movie.name}"
            )
            await self.torrent_service.resume_download(torrent=movie_torrent)
        return movie_torrent

    @staticmethod
    def _default_file_path_suffix(indexer_result: IndexerQueryResult) -> str:
        """
        Default file path suffix for a download that didn't get an explicit
        override: the label of the slot the release's stored attributes
        match (e.g. "1080p Encode", "4K Remux"), or none if it didn't match a
        configured slot. Sanitized since it ends up as part of a filename on
        disk.
        """
        label = resolve_slot_label(indexer_result)
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
