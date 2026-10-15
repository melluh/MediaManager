import asyncio
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import ColumnElement, delete, or_, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import media_manager.metadataProvider.utils
from media_manager.movies.models import Movie
from media_manager.rating.models import MediaRating, RatingPromptDismissal
from media_manager.torrent.schemas import TorrentMedia


class RatingRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def _media_filter(
        movie_id: UUID | None, show_id: UUID | None
    ) -> ColumnElement[bool]:
        if movie_id is not None:
            return MediaRating.movie_id == movie_id
        return MediaRating.show_id == show_id

    async def get_score(
        self,
        user_id: UUID,
        *,
        movie_id: UUID | None = None,
        show_id: UUID | None = None,
    ) -> int | None:
        stmt = select(MediaRating.score).where(
            MediaRating.user_id == user_id, self._media_filter(movie_id, show_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def set_score(
        self,
        user_id: UUID,
        score: int,
        *,
        movie_id: UUID | None = None,
        show_id: UUID | None = None,
    ) -> None:
        stmt = pg_insert(MediaRating).values(
            id=uuid.uuid4(),
            user_id=user_id,
            movie_id=movie_id,
            show_id=show_id,
            score=score,
            rated_at=datetime.now(UTC),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "movie_id" if movie_id else "show_id"],
            set_={"score": stmt.excluded.score, "rated_at": stmt.excluded.rated_at},
        )
        try:
            await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def delete_score(
        self,
        user_id: UUID,
        *,
        movie_id: UUID | None = None,
        show_id: UUID | None = None,
    ) -> None:
        stmt = delete(MediaRating).where(
            MediaRating.user_id == user_id, self._media_filter(movie_id, show_id)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def dismiss_prompt(self, user_id: UUID, movie_id: UUID) -> None:
        stmt = (
            pg_insert(RatingPromptDismissal)
            .values(user_id=user_id, movie_id=movie_id, dismissed_at=datetime.now(UTC))
            .on_conflict_do_nothing()
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_answered_movie_ids(self, user_id: UUID) -> set[UUID]:
        """Movies the user has rated or chosen not to rate."""
        rated = select(MediaRating.movie_id).where(
            MediaRating.user_id == user_id, MediaRating.movie_id.is_not(None)
        )
        dismissed = select(RatingPromptDismissal.movie_id).where(
            RatingPromptDismissal.user_id == user_id
        )
        return set((await self.db.execute(rated.union(dismissed))).scalars())

    async def find_movies(
        self,
        imdb_ids: set[str],
        external_ids: set[tuple[str, int]],
    ) -> list[tuple[Movie, TorrentMedia]]:
        """
        Library movies with any of these IMDb ids or (metadata provider,
        external id) pairs, each with a poster-ready summary.
        """
        conditions = []
        if imdb_ids:
            conditions.append(Movie.imdb_id.in_(imdb_ids))
        if external_ids:
            conditions.append(
                tuple_(Movie.metadata_provider, Movie.external_id).in_(external_ids)
            )
        if not conditions:
            return []
        movies = list(
            (await self.db.execute(select(Movie).where(or_(*conditions))))
            .scalars()
            .unique()
        )
        if not movies:
            return []
        images = await asyncio.to_thread(
            media_manager.metadataProvider.utils.get_available_media_images_many,
            [movie.id for movie in movies],
        )
        return [
            (
                movie,
                TorrentMedia.from_media(
                    movie, is_show=False, images=images.get(str(movie.id), {})
                ),
            )
            for movie in movies
        ]
