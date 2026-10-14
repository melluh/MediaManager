import asyncio
import logging
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import false

import media_manager.metadataProvider.utils
from media_manager.exceptions import ConflictError, NotFoundError
from media_manager.movies.models import Movie
from media_manager.notification.models import Notification
from media_manager.notification.schemas import (
    Notification as NotificationSchema,
)
from media_manager.notification.schemas import (
    NotificationId,
)
from media_manager.torrent.schemas import TorrentMedia
from media_manager.tv.models import Show

log = logging.getLogger(__name__)


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _to_schemas(
        self, notifications: Sequence[Notification]
    ) -> list[NotificationSchema]:
        """
        Converts rows to schemas, attaching a summary of each linked movie/show
        so the UI can show its poster. Resolved in one query per media type and
        one batched image lookup, however many notifications there are.
        """
        movie_ids = {n.movie_id for n in notifications if n.movie_id}
        show_ids = {n.show_id for n in notifications if n.show_id}
        movies = (
            {
                m.id: m
                for m in (
                    await self.db.execute(select(Movie).where(Movie.id.in_(movie_ids)))
                ).scalars()
            }
            if movie_ids
            else {}
        )
        shows = (
            {
                s.id: s
                for s in (
                    await self.db.execute(select(Show).where(Show.id.in_(show_ids)))
                ).scalars()
            }
            if show_ids
            else {}
        )
        images_by_media_id = (
            await asyncio.to_thread(
                media_manager.metadataProvider.utils.get_available_media_images_many,
                [*movies, *shows],
            )
            if movies or shows
            else {}
        )

        results = []
        for notification in notifications:
            schema = NotificationSchema.model_validate(notification)
            movie = movies.get(notification.movie_id) if notification.movie_id else None
            show = shows.get(notification.show_id) if notification.show_id else None
            if media := movie or show:
                schema.media = TorrentMedia.from_media(
                    media,
                    is_show=media is show,
                    images=images_by_media_id.get(str(media.id), {}),
                )
            results.append(schema)
        return results

    async def get_notification(
        self, nid: NotificationId, user_id: UUID
    ) -> NotificationSchema:
        result = await self.db.get(Notification, nid)

        # A notification of another user is reported as missing, so its
        # existence isn't revealed.
        if not result or result.user_id != user_id:
            msg = f"Notification with id {nid} not found."
            raise NotFoundError(msg)

        return (await self._to_schemas([result]))[0]

    async def get_unread_notifications(self, user_id: UUID) -> list[NotificationSchema]:
        try:
            stmt = (
                select(Notification)
                .where(Notification.user_id == user_id, Notification.read == false())
                .order_by(Notification.timestamp.desc())
            )
            results = (await self.db.execute(stmt)).scalars().all()
            return await self._to_schemas(results)
        except SQLAlchemyError:
            log.exception("Database error while retrieving unread notifications")
            raise

    async def get_unread_notification_count(self, user_id: UUID) -> int:
        try:
            stmt = (
                select(func.count())
                .select_from(Notification)
                .where(Notification.user_id == user_id, Notification.read == false())
            )
            return (await self.db.execute(stmt)).scalar_one()
        except SQLAlchemyError:
            log.exception("Database error while counting unread notifications")
            raise

    async def get_all_notifications(self, user_id: UUID) -> list[NotificationSchema]:
        try:
            stmt = (
                select(Notification)
                .where(Notification.user_id == user_id)
                .order_by(Notification.timestamp.desc())
            )
            results = (await self.db.execute(stmt)).scalars().all()
            return await self._to_schemas(results)
        except SQLAlchemyError:
            log.exception("Database error while retrieving notifications")
            raise

    async def save_notification(self, notification: NotificationSchema) -> None:
        try:
            self.db.add(
                Notification(
                    id=notification.id,
                    user_id=notification.user_id,
                    read=notification.read,
                    timestamp=notification.timestamp,
                    message=notification.message,
                    movie_id=notification.movie_id,
                    show_id=notification.show_id,
                )
            )
            await self.db.commit()
        except IntegrityError:
            # AsyncSession leaves the txn in invalid state on IntegrityError;
            # without rollback the request-end commit raises PendingRollbackError.
            await self.db.rollback()
            log.exception("Could not save notification")
            msg = f"Notification with id {notification.id} already exists."
            raise ConflictError(msg) from None

    async def _set_read(self, nid: NotificationId, user_id: UUID, read: bool) -> None:
        stmt = (
            update(Notification)
            .where(Notification.id == nid, Notification.user_id == user_id)
            .values(read=read)
        )
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            msg = f"Notification with id {nid} not found."
            raise NotFoundError(msg)

    async def mark_notification_as_read(
        self, nid: NotificationId, user_id: UUID
    ) -> None:
        await self._set_read(nid=nid, user_id=user_id, read=True)

    async def mark_all_notifications_as_read(self, user_id: UUID) -> None:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read == false())
            .values(read=True)
        )
        await self.db.execute(stmt)

    async def mark_notification_as_unread(
        self, nid: NotificationId, user_id: UUID
    ) -> None:
        await self._set_read(nid=nid, user_id=user_id, read=False)

    async def delete_notification(self, nid: NotificationId, user_id: UUID) -> None:
        stmt = delete(Notification).where(
            Notification.id == nid, Notification.user_id == user_id
        )
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            msg = f"Notification with id {nid} not found."
            raise NotFoundError(msg)
        await self.db.commit()
