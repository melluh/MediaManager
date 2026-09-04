import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from media_manager.common.repository import BaseRepository
from media_manager.exceptions import NotFoundError
from media_manager.movies.models import Movie, MovieFile
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
from media_manager.torrent.schemas import Quality, TorrentId

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

    async def set_movie_file_relative_path(
        self, movie_id: MovieId, file_path_suffix: str, relative_path: str | None
    ) -> None:
        """
        Records where a movie file was actually written, for a record that was
        created before its file existed. None means no file is known for the
        record, which is what the library scan writes when the file it pointed
        at is gone.
        """
        stmt = (
            update(MovieFile)
            .where(
                MovieFile.movie_id == movie_id,
                MovieFile.file_path_suffix == file_path_suffix,
            )
            .values(relative_path=relative_path)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def remove_movie_files_by_torrent_id(self, torrent_id: TorrentId) -> int:
        return await self.remove_files_by_torrent_id_base(
            torrent_id=torrent_id, model_class=MovieFile
        )

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

    async def get_movie_downloaded_statuses(self) -> dict[MovieId, bool]:
        """
        A movie is downloaded if any of its MovieFiles is either not tied
        to a torrent (manually imported) or tied to a torrent that has
        finished importing - the same semantics as
        `MovieService.movie_file_exists_on_file`, computed in bulk for the
        downloaded-status scan instead of per movie/file at request time.

        Seeds every movie (including ones with no files at all) to False
        first, so the scan always produces a cache entry - otherwise movies
        with zero files would never get one and would keep hitting the
        request-path fallback query forever.
        """
        all_movie_ids = (await self.db.execute(select(Movie.id))).scalars().all()
        statuses: dict[MovieId, bool] = dict.fromkeys(all_movie_ids, False)

        stmt = select(
            MovieFile.movie_id, MovieFile.torrent_id, Torrent.imported
        ).select_from(MovieFile).outerjoin(Torrent, MovieFile.torrent_id == Torrent.id)
        rows = (await self.db.execute(stmt)).all()

        for movie_id, torrent_id, imported in rows:
            downloaded = torrent_id is None or bool(imported)
            statuses[movie_id] = statuses.get(movie_id, False) or downloaded
        return statuses

    async def get_movie_download_info(
        self,
    ) -> dict[MovieId, tuple[bool, Quality | None]]:
        """
        For every movie, whether it's downloaded and (if so) the best quality
        among its downloaded files - the same downloaded semantics as
        `get_movie_downloaded_statuses`, computed in bulk for the movie list
        endpoint's filters instead of per movie at request time.
        """
        all_movie_ids = (await self.db.execute(select(Movie.id))).scalars().all()
        info: dict[MovieId, tuple[bool, Quality | None]] = dict.fromkeys(
            all_movie_ids, (False, None)
        )

        stmt = select(
            MovieFile.movie_id, MovieFile.torrent_id, MovieFile.quality, Torrent.imported
        ).select_from(MovieFile).outerjoin(Torrent, MovieFile.torrent_id == Torrent.id)
        rows = (await self.db.execute(stmt)).all()

        for movie_id, torrent_id, quality, imported in rows:
            downloaded = torrent_id is None or bool(imported)
            if not downloaded:
                continue
            _, best_quality = info.get(movie_id, (False, None))
            if best_quality is None or quality.value < best_quality.value:
                best_quality = quality
            info[movie_id] = (True, best_quality)
        return info

    async def get_torrents_by_movie_id(
        self, movie_id: MovieId
    ) -> list[MovieTorrentSchema]:
        try:
            stmt = (
                select(Torrent, MovieFile.file_path_suffix)
                .distinct()
                .join(MovieFile, MovieFile.torrent_id == Torrent.id)
                .where(MovieFile.movie_id == movie_id)
            )
            results = (await self.db.execute(stmt)).all()
            formatted_results = []
            for torrent, file_path_suffix in results:
                movie_torrent = MovieTorrentSchema(
                    torrent_id=torrent.id,
                    torrent_title=torrent.title,
                    status=torrent.status,
                    quality=torrent.quality,
                    imported=torrent.imported,
                    file_path_suffix=file_path_suffix,
                    usenet=torrent.usenet,
                )
                formatted_results.append(movie_torrent)
        except SQLAlchemyError:
            log.exception(f"Database error retrieving torrents for movie_id {movie_id}")
            raise
        else:
            return formatted_results

    async def get_all_movies_with_torrents(self) -> list[MovieSchema]:
        try:
            stmt = (
                select(Movie)
                .distinct()
                .join(MovieFile, Movie.id == MovieFile.movie_id)
                .join(Torrent, MovieFile.torrent_id == Torrent.id)
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
                .join(MovieFile, Movie.id == MovieFile.movie_id)
                .where(MovieFile.torrent_id == torrent_id)
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
