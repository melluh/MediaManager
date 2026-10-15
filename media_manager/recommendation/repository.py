from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from media_manager.metadataProvider.schemas import (
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.models import Movie
from media_manager.rating.models import MediaRating
from media_manager.recommendation.models import TmdbRecommendationList
from media_manager.recommendation.schemas import RatedMedia
from media_manager.tv.models import Show
from media_manager.watch_history.models import MediaWatch


def _media_model(media_type: MediaType) -> type[Movie] | type[Show]:
    return Movie if media_type == MediaType.movie else Show


class RecommendationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_rated_media(
        self, user_id: UUID, media_type: MediaType
    ) -> list[RatedMedia]:
        """Every movie or show the user rated, with its metadata."""
        model = _media_model(media_type)
        rating_media_id = (
            MediaRating.movie_id
            if media_type == MediaType.movie
            else MediaRating.show_id
        )
        stmt = (
            select(
                model.name,
                model.metadata_provider,
                model.external_id,
                model.imdb_id,
                model.genres,
                MediaRating.score,
                MediaRating.rated_at,
            )
            .join(model, model.id == rating_media_id)
            .where(MediaRating.user_id == user_id)
        )
        return [
            RatedMedia(
                name=row.name,
                metadata_provider=row.metadata_provider,
                external_id=row.external_id,
                imdb_id=row.imdb_id,
                genres=row.genres or [],
                score=row.score,
                rated_at=row.rated_at,
            )
            for row in await self.db.execute(stmt)
        ]

    async def get_user_ids_with_history(self) -> list[UUID]:
        """Users who rated or watched anything, i.e. who can get
        recommendations."""
        stmt = select(MediaRating.user_id).union(select(MediaWatch.user_id))
        return list((await self.db.execute(stmt)).scalars())

    async def get_lists(
        self, media_type: MediaType, tmdb_ids: set[int]
    ) -> dict[int, TmdbRecommendationList]:
        if not tmdb_ids:
            return {}
        stmt = select(TmdbRecommendationList).where(
            TmdbRecommendationList.media_type == media_type.value,
            TmdbRecommendationList.tmdb_id.in_(tmdb_ids),
        )
        return {row.tmdb_id: row for row in (await self.db.execute(stmt)).scalars()}

    async def save_list(
        self,
        media_type: MediaType,
        tmdb_id: int,
        results: list[MetaDataProviderSearchResult] | None,
    ) -> None:
        """Stores a freshly fetched list, or None to record a failed fetch."""
        values = {
            "fetched_at": datetime.now(UTC),
            "results": None
            if results is None
            else [result.model_dump(mode="json") for result in results],
        }
        stmt = pg_insert(TmdbRecommendationList).values(
            media_type=media_type.value, tmdb_id=tmdb_id, **values
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["media_type", "tmdb_id"], set_=values
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def find_library_media(
        self, media_type: MediaType, tmdb_ids: set[int]
    ) -> dict[int, tuple[UUID, str]]:
        """Library movies or shows with these TMDB ids: tmdb id -> (id, slug)."""
        if not tmdb_ids:
            return {}
        model = _media_model(media_type)
        stmt = select(model.external_id, model.id, model.slug).where(
            tuple_(model.metadata_provider, model.external_id).in_(
                [("tmdb", tmdb_id) for tmdb_id in tmdb_ids]
            )
        )
        return {
            row.external_id: (row.id, row.slug) for row in await self.db.execute(stmt)
        }
