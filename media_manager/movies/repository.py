import logging
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from media_manager.common.repository import BaseRepository
from media_manager.common.schemas import MediaFileDetails
from media_manager.exceptions import NotFoundError
from media_manager.movies.models import Movie, MovieDownload, MovieFile
from media_manager.movies.schemas import (
    Movie as MovieSchema,
)
from media_manager.movies.schemas import (
    MovieFile as MovieFileSchema,
)
from media_manager.movies.schemas import (
    MovieId,
)
from media_manager.movies.schemas import (
    MovieTorrent as MovieTorrentSchema,
)
from media_manager.torrent.models import Torrent
from media_manager.torrent.schemas import Torrent as TorrentSchema
from media_manager.torrent.schemas import TorrentId

log = logging.getLogger(__name__)


class MovieRepository(BaseRepository[Movie, MovieSchema]):
    """
    Repository for managing movies in the database.
    Provides methods to retrieve, save, and delete movies.
    """

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Movie, MovieSchema)

    async def get_movie_by_id(self, movie_id: MovieId) -> MovieSchema:
        return await self.get_by_id(entity_id=movie_id)

    async def get_movie_by_external_id(
        self, external_id: int, metadata_provider: str
    ) -> MovieSchema:
        return await self.get_by_external_id(
            external_id=external_id, metadata_provider=metadata_provider
        )

    async def get_movies(self) -> list[MovieSchema]:
        return await self.get_all()

    async def count_movies(self) -> int:
        stmt = select(func.count(Movie.id))
        result = (await self.db.execute(stmt)).scalar_one_or_none()
        return result or 0

    async def delete_movie(self, movie_id: MovieId) -> None:
        await self.delete(entity_id=movie_id)

    async def set_movie_library(self, movie_id: MovieId, library: str) -> None:
        await self.set_library(entity_id=movie_id, library=library)

    async def save_movie(self, movie: MovieSchema) -> MovieSchema:
        return await self.save_media_base(media_schema=movie, model_class=Movie)

    async def get_movie_by_slug(self, slug: str) -> MovieSchema:
        stmt = select(Movie).where(Movie.slug == slug)
        result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if not result:
            msg = f"Movie with slug {slug} not found."
            raise NotFoundError(msg)
        return MovieSchema.model_validate(result)

    async def add_movie_file(self, movie_file: MovieFileSchema) -> MovieFileSchema:
        return await self.add_media_file_base(
            file_schema=movie_file, model_class=MovieFile, schema_class=MovieFileSchema
        )

    async def add_movie_files_bulk(self, movie_files: list[MovieFileSchema]) -> None:
        await self.add_media_files_bulk_base(
            file_schemas=movie_files, model_class=MovieFile
        )

    async def upsert_movie_file(self, movie_file: MovieFileSchema) -> None:
        """Records an imported movie file, replacing any file already
        recorded for the same movie and file path suffix."""
        await self.upsert_media_file_base(
            file_schema=movie_file,
            model_class=MovieFile,
            owner_column=MovieFile.movie_id,
        )

    async def set_movie_file_relative_paths_bulk(
        self, updates: list[tuple[MovieId, str, str]]
    ) -> None:
        """
        Relinks existing movie file records to where their file is now
        ((movie_id, file_path_suffix, relative_path) triples), in a single
        transaction.
        """
        await self.set_media_file_relative_paths_base(
            model_class=MovieFile, owner_column=MovieFile.movie_id, updates=updates
        )

    async def delete_movie_files(self, keys: list[tuple[MovieId, str]]) -> None:
        """Deletes the movie file records with the given (movie_id, file_path_suffix) keys."""
        await self.delete_media_files_base(
            model_class=MovieFile, owner_column=MovieFile.movie_id, keys=keys
        )

    async def update_movie_file_details(self, movie_files: list[MovieFileSchema]) -> None:
        """Stores freshly probed details for the given movie files."""
        await self.update_media_file_details_base(
            model_class=MovieFile,
            owner_column=MovieFile.movie_id,
            files=movie_files,
            owner_field="movie_id",
        )

    async def add_movie_download(
        self, torrent_id: TorrentId, movie_id: MovieId, file_path_suffix: str
    ) -> None:
        """Links a torrent to the movie it's downloading, and the file path
        suffix its file is to be imported as."""
        self.db.add(
            MovieDownload(
                torrent_id=torrent_id,
                movie_id=movie_id,
                file_path_suffix=file_path_suffix,
            )
        )
        try:
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_taken_movie_file_path_suffixes(self, movie_id: MovieId) -> set[str]:
        """
        File path suffixes a new download for this movie can't use: those of
        files already in the library, and those of downloads still headed for
        it (neither imported nor cancelled).
        """
        files_stmt = select(MovieFile.file_path_suffix).where(
            MovieFile.movie_id == movie_id
        )
        downloads_stmt = (
            select(MovieDownload.file_path_suffix)
            .join(Torrent, Torrent.id == MovieDownload.torrent_id)
            .where(
                MovieDownload.movie_id == movie_id,
                ~Torrent.imported,
                ~Torrent.cancelled,
            )
        )
        stmt = files_stmt.union(downloads_stmt)
        return set((await self.db.execute(stmt)).scalars().all())

    async def get_movie_files_by_movie_id(
        self, movie_id: MovieId
    ) -> list[MovieFileSchema]:
        try:
            stmt = select(MovieFile).where(MovieFile.movie_id == movie_id)
            results = (await self.db.execute(stmt)).scalars().all()
            return [MovieFileSchema.model_validate(sf) for sf in results]
        except SQLAlchemyError:
            log.exception(
                f"Database error retrieving movie files for movie_id {movie_id}"
            )
            raise

    async def get_all_movie_files_grouped_by_movie(
        self,
    ) -> dict[MovieId, list[MovieFileSchema]]:
        """
        Every movie file in the library, grouped by movie - one query for the
        whole library scan instead of one per movie.
        """
        results = (await self.db.execute(select(MovieFile))).scalars().all()
        grouped: dict[MovieId, list[MovieFileSchema]] = {}
        for movie_file in results:
            grouped.setdefault(MovieId(movie_file.movie_id), []).append(
                MovieFileSchema.model_validate(movie_file)
            )
        return grouped

    async def get_movie_ids_with_files(
        self, movie_ids: Sequence[MovieId]
    ) -> set[MovieId]:
        """Which of the given movies have at least one file in the library."""
        return await self.get_owners_with_files_base(
            owner_ids=movie_ids, owner_column=MovieFile.movie_id
        )

    async def get_all_movie_file_details(
        self,
    ) -> dict[MovieId, list[MediaFileDetails | None]]:
        """
        Every movie's stored file probe details (None for a file not probed
        yet), keyed by movie - one query for the movie list's filters.
        Movies with no files are absent.
        """
        stmt = select(MovieFile.movie_id, MovieFile.details)
        grouped: dict[MovieId, list[MediaFileDetails | None]] = {}
        for movie_id, details in (await self.db.execute(stmt)).all():
            grouped.setdefault(MovieId(movie_id), []).append(
                MediaFileDetails.model_validate(details) if details else None
            )
        return grouped

    async def get_torrents_by_movie_id(
        self, movie_id: MovieId
    ) -> list[MovieTorrentSchema]:
        try:
            stmt = (
                select(Torrent, MovieDownload.file_path_suffix)
                .join(MovieDownload, MovieDownload.torrent_id == Torrent.id)
                .where(MovieDownload.movie_id == movie_id)
            )
            results = (await self.db.execute(stmt)).all()
            formatted_results = []
            for torrent, file_path_suffix in results:
                movie_torrent = MovieTorrentSchema(
                    torrent_id=torrent.id,
                    torrent_title=torrent.title,
                    status=torrent.status,
                    slot=torrent.slot,
                    imported=torrent.imported,
                    cancelled=torrent.cancelled,
                    file_path_suffix=file_path_suffix,
                    usenet=torrent.usenet,
                )
                formatted_results.append(movie_torrent)
        except SQLAlchemyError:
            log.exception(f"Database error retrieving torrents for movie_id {movie_id}")
            raise
        else:
            return formatted_results

    async def get_full_torrents_by_movie_id(self, movie_id: MovieId) -> list[TorrentSchema]:
        try:
            stmt = (
                select(Torrent)
                .join(MovieDownload, MovieDownload.torrent_id == Torrent.id)
                .where(MovieDownload.movie_id == movie_id)
            )
            results = (await self.db.execute(stmt)).scalars().unique().all()
        except SQLAlchemyError:
            log.exception(f"Database error retrieving torrents for movie_id {movie_id}")
            raise
        else:
            return [TorrentSchema.model_validate(t) for t in results]

    async def get_all_movies_with_torrents(self) -> list[MovieSchema]:
        try:
            stmt = (
                select(Movie)
                .distinct()
                .join(MovieDownload, Movie.id == MovieDownload.movie_id)
                .order_by(Movie.name)
            )
            results = (await self.db.execute(stmt)).scalars().unique().all()
            return [MovieSchema.model_validate(movie) for movie in results]
        except SQLAlchemyError:
            log.exception("Database error retrieving all movies with torrents")
            raise

    async def get_movie_by_torrent_id(self, torrent_id: TorrentId) -> MovieSchema:
        try:
            stmt = (
                select(Movie)
                .join(MovieDownload, Movie.id == MovieDownload.movie_id)
                .where(MovieDownload.torrent_id == torrent_id)
            )
            result = (await self.db.execute(stmt)).unique().scalar_one_or_none()
            if not result:
                msg = f"Movie for torrent_id {torrent_id} not found."
                raise NotFoundError(msg)
        except SQLAlchemyError:
            log.exception(f"Database error retrieving movie by torrent_id {torrent_id}")
            raise
        else:
            return MovieSchema.model_validate(result)

    async def update_movie_attributes(
        self,
        movie_id: MovieId,
        name: str | None = None,
        overview: str | None = None,
        year: int | None = None,
        imdb_id: str | None = None,
        tagline: str | None = None,
        genres: list[str] | None = None,
        runtime: int | None = None,
        release_date: str | None = None,
        metadata_updated_at: datetime | None = None,
        metadata_version: int | None = None,
    ) -> MovieSchema:
        return await self.update_media_attributes_base(
            media_id=movie_id,
            model_class=Movie,
            name=name,
            overview=overview,
            year=year,
            imdb_id=imdb_id,
            tagline=tagline,
            genres=genres,
            runtime=runtime,
            release_date=release_date,
            metadata_updated_at=metadata_updated_at,
            metadata_version=metadata_version,
        )
