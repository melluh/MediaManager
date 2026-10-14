from uuid import UUID

from media_manager.notification.manager import notification_manager
from media_manager.notification.repository import NotificationRepository
from media_manager.notification.schemas import Notification, NotificationId


class NotificationService:
    def __init__(
        self,
        notification_repository: NotificationRepository,
    ) -> None:
        self.notification_repository = notification_repository
        self.notification_manager = notification_manager

    async def get_notification(
        self, nid: NotificationId, user_id: UUID
    ) -> Notification:
        return await self.notification_repository.get_notification(
            nid=nid, user_id=user_id
        )

    async def get_unread_notifications(self, user_id: UUID) -> list[Notification]:
        return await self.notification_repository.get_unread_notifications(
            user_id=user_id
        )

    async def get_unread_notification_count(self, user_id: UUID) -> int:
        return await self.notification_repository.get_unread_notification_count(
            user_id=user_id
        )

    async def get_all_notifications(self, user_id: UUID) -> list[Notification]:
        return await self.notification_repository.get_all_notifications(user_id=user_id)

    async def save_notification(self, notification: Notification) -> None:
        return await self.notification_repository.save_notification(notification)

    async def mark_notification_as_read(
        self, nid: NotificationId, user_id: UUID
    ) -> None:
        return await self.notification_repository.mark_notification_as_read(
            nid=nid, user_id=user_id
        )

    async def mark_all_notifications_as_read(self, user_id: UUID) -> None:
        return await self.notification_repository.mark_all_notifications_as_read(
            user_id=user_id
        )

    async def mark_notification_as_unread(
        self, nid: NotificationId, user_id: UUID
    ) -> None:
        return await self.notification_repository.mark_notification_as_unread(
            nid=nid, user_id=user_id
        )

    async def delete_notification(self, nid: NotificationId, user_id: UUID) -> None:
        return await self.notification_repository.delete_notification(
            nid=nid, user_id=user_id
        )

    async def send_notification(
        self,
        title: str,
        message: str,
        *,
        user_id: UUID | None,
        movie_id: UUID | None = None,
        show_id: UUID | None = None,
    ) -> None:
        """
        Sends the notification to every configured external provider (a
        server-wide feed for the admin) and, if `user_id` is given, to that
        user's in-app notifications. With no user - e.g. a download whose
        initiator is unknown - only the external providers get it.

        :param movie_id: The movie the notification is about, if any.
        :param show_id: The show the notification is about, if any.
        """
        await self.notification_manager.send_notification(title, message)

        if user_id is None:
            return
        internal_notification = Notification(
            user_id=user_id,
            message=f"{title}: {message}",
            read=False,
            movie_id=movie_id,
            show_id=show_id,
        )
        await self.save_notification(internal_notification)
