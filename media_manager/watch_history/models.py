from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from media_manager.database import Base


class MediaWatch(Base):
    """
    A movie or show a user has watched on the media server, synced from it so
    watch history is available without asking the server each time. A show
    counts as watched once any of its episodes has been.

    Keyed by the media server's item and storing its external ids rather than
    referencing library media, since users also watch titles the library
    doesn't manage.
    """

    __tablename__ = "media_watch"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    media_type: Mapped[str] = mapped_column(primary_key=True)
    """A `MediaType` value."""
    server_item_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    imdb_id: Mapped[str | None] = mapped_column(default=None)
    tmdb_id: Mapped[int | None] = mapped_column(default=None)
    tvdb_id: Mapped[int | None] = mapped_column(default=None)
    last_played_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """None for items marked as played by hand, which have no play date."""
