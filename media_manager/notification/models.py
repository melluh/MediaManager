from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from media_manager.database import Base


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    """The user this notification is shown to."""
    message: Mapped[str]
    read: Mapped[bool]
    timestamp = mapped_column(DateTime, nullable=False)
    movie_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("movie.id", ondelete="SET NULL"), default=None
    )
    """The movie this notification is about, if any."""
    show_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("show.id", ondelete="SET NULL"), default=None
    )
    """The show this notification is about, if any."""
