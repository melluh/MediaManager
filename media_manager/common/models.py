from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from media_manager.database import Base

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
    Mixin for common media file fields used by both Movie files and Episode
    files. A row exists only for a file that has actually been imported to (or
    found in) the library - a download in progress is a MovieDownload /
    EpisodeDownload, not a file.
    """

    file_path_suffix: Mapped[str]
    relative_path: Mapped[str]
    """Path of the file relative to the media's root directory."""
    torrent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(column="torrent.id", ondelete="SET NULL"),
    )
    """The torrent the file was imported from, if any."""
    details = mapped_column(JSONB, nullable=True)
    """`MediaFileDetails` from the last probe of the file, NULL until probed."""
    probed_mtime_ns: Mapped[int | None] = mapped_column(BigInteger, default=None)
    """The file's mtime when `details` was probed, to tell when it's stale."""


class MediaImage(Base):
    """
    Tracks the provider path/URL last used to download each on-disk image,
    so a metadata refresh can tell whether an image actually changed before
    re-downloading it.

    Not scoped to a single parent table by FK: `media_id` may belong to a
    Movie, Show, or Season, mirroring the on-disk image layout
    (`media_image_relative_path` in `metadataProvider/utils.py`), which is
    also keyed by `media_id` alone regardless of media type.
    """

    __tablename__ = "media_image"
    __table_args__ = (PrimaryKeyConstraint("media_id", "image_type"),)

    media_id: Mapped[UUID]
    image_type: Mapped[str]
    source_path: Mapped[str]
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
