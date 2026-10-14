import typing
import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from media_manager.torrent.schemas import TorrentMedia

NotificationId = typing.NewType("NotificationId", UUID)


class Notification(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: NotificationId = Field(
        default_factory=lambda: NotificationId(uuid.uuid4()),
        description="Unique identifier for the notification",
    )
    user_id: UUID = Field(description="The user this notification is shown to")
    read: bool = Field(False, description="Whether the notification has been read")
    message: str = Field(description="The content of the notification")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="The timestamp of the notification"
    )
    movie_id: UUID | None = Field(
        None, description="The movie this notification is about, if any"
    )
    show_id: UUID | None = Field(
        None, description="The show this notification is about, if any"
    )
    media: TorrentMedia | None = Field(
        None,
        description="Summary of the linked movie/show for rendering a poster and "
        "link; resolved when read, not stored",
    )


class MessageNotification(BaseModel):
    """
    Notification type for messages.
    """

    message: str
    title: str
