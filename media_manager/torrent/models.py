from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from media_manager.database import Base
from media_manager.torrent.schemas import Quality, TorrentStatus


class Torrent(Base):
    __tablename__ = "torrent"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    status: Mapped[TorrentStatus]
    title: Mapped[str]
    quality: Mapped[Quality]
    imported: Mapped[bool]
    import_error: Mapped[str | None] = mapped_column(default=None)
    import_error_kind: Mapped[str | None] = mapped_column(default=None)
    """Stored as plain text (not a native enum column) since ImportErrorKind is expected to grow over time."""
    hash: Mapped[str]
    usenet: Mapped[bool]
    initiated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), default=None
    )
    initiated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    indexer: Mapped[str | None] = mapped_column(default=None)
    comments: Mapped[str | None] = mapped_column(default=None)

    episode_files = relationship("EpisodeFile", back_populates="torrent")
    movie_files = relationship("MovieFile", back_populates="torrent")
