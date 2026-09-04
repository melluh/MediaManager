from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from media_manager.torrent.models import Quality

if TYPE_CHECKING:
    from media_manager.auth.db import User


class MediaMixin:
    """
    Mixin for common media fields used by both Movies and TV Shows.
    """

    id: Mapped[UUID] = mapped_column(primary_key=True)
    external_id: Mapped[int] = mapped_column(index=True)
    metadata_provider: Mapped[str]
    name: Mapped[str]
    slug: Mapped[str]
    directory_name: Mapped[str]
    """Basename of the media's own directory on disk; the parent directory is
    resolved from `library` at read time, so a library can still be moved."""
    overview: Mapped[str]
    year: Mapped[int | None]
    library: Mapped[str] = mapped_column(default="Default")
    original_language: Mapped[str | None] = mapped_column(default=None)
    imdb_id: Mapped[str | None] = mapped_column(default=None)
    trailer_url: Mapped[str | None] = mapped_column(default=None)
    tagline: Mapped[str | None] = mapped_column(default=None)
    genres = mapped_column(ARRAY(String), nullable=True, default=list)
    runtime: Mapped[int | None] = mapped_column(default=None)
    release_date: Mapped[str | None] = mapped_column(default=None)
    metadata_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    metadata_version: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    """When this media item was added to the library."""
    added_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(column="user.id", ondelete="SET NULL"), default=None
    )
    """The user who added this media item, if known and not since deleted."""

    @declared_attr
    def added_by(cls) -> Mapped["User"]:  # noqa: N805
        # Declared per-subclass (rather than as a plain mixin attribute)
        # because the FK it joins on (`added_by_user_id`) is also defined on
        # this mixin - a shared relationship object would otherwise be
        # copied onto both Movie and Show, which SQLAlchemy rejects.
        return relationship("User", lazy="joined", viewonly=True)


class MediaFileMixin:
    """
    Mixin for common media file fields used by both Movie files and Episode files.
    """

    file_path_suffix: Mapped[str]
    quality: Mapped[Quality]
    relative_path: Mapped[str | None] = mapped_column(default=None)
    """Path of the file relative to the media's root directory, or NULL when no
    file is known to have been written yet."""
    torrent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(column="torrent.id", ondelete="SET NULL"),
    )
