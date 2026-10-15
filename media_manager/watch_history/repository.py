from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from media_manager.auth.db import MediaServerAccount, User
from media_manager.mediaServer.schemas import PlayedMediaItem
from media_manager.metadataProvider.schemas import MediaType
from media_manager.watch_history.models import MediaWatch

_INSERT_BATCH_SIZE = 1000
"""Rows per insert, keeping a long watch history well under Postgres' limit
on bind parameters per statement."""


def _numeric_id(value: str | None) -> int | None:
    return int(value) if value is not None and value.isdigit() else None


class WatchHistoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_watches(
        self,
        user_id: UUID,
        media_type: MediaType,
        items: list[PlayedMediaItem],
        *,
        replace: bool,
    ) -> None:
        """
        Inserts or updates the user's watches of `media_type`. With
        `replace`, `items` is the user's whole history, so watches missing
        from it (e.g. marked unplayed since) are deleted.
        """
        rows = {
            item.server_item_id: {
                "user_id": user_id,
                "media_type": media_type.value,
                "server_item_id": item.server_item_id,
                "name": item.name,
                "imdb_id": item.provider_ids.get("imdb"),
                "tmdb_id": _numeric_id(item.provider_ids.get("tmdb")),
                "tvdb_id": _numeric_id(item.provider_ids.get("tvdb")),
                "last_played_at": item.last_played_at,
            }
            for item in items
        }
        try:
            if replace:
                await self.db.execute(
                    delete(MediaWatch).where(
                        MediaWatch.user_id == user_id,
                        MediaWatch.media_type == media_type.value,
                        MediaWatch.server_item_id.not_in(rows),
                    )
                )
            values = list(rows.values())
            for i in range(0, len(values), _INSERT_BATCH_SIZE):
                stmt = pg_insert(MediaWatch).values(values[i : i + _INSERT_BATCH_SIZE])
                stmt = stmt.on_conflict_do_update(
                    index_elements=["user_id", "media_type", "server_item_id"],
                    set_={
                        column: stmt.excluded[column]
                        for column in (
                            "name",
                            "imdb_id",
                            "tmdb_id",
                            "tvdb_id",
                            "last_played_at",
                        )
                    },
                )
                await self.db.execute(stmt)
            await self.db.commit()
        except SQLAlchemyError:
            await self.db.rollback()
            raise

    async def get_watches(
        self, user_id: UUID, media_type: MediaType
    ) -> list[MediaWatch]:
        stmt = select(MediaWatch).where(
            MediaWatch.user_id == user_id, MediaWatch.media_type == media_type.value
        )
        return list((await self.db.execute(stmt)).scalars())

    async def get_users_with_account(self, provider: str) -> list[User]:
        """Users with an account linked on the given media server."""
        stmt = (
            select(User)
            .join(MediaServerAccount, MediaServerAccount.user_id == User.id)
            .where(MediaServerAccount.provider == provider)
        )
        return list((await self.db.execute(stmt)).scalars().unique())
