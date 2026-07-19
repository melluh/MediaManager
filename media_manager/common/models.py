from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from media_manager.torrent.models import Quality


class MediaMixin:
    """
    Mixin for common media fields used by both Movies and TV Shows.
    """

    id: Mapped[UUID] = mapped_column(primary_key=True)
    external_id: Mapped[int] = mapped_column(index=True)
    metadata_provider: Mapped[str]
    name: Mapped[str]
    overview: Mapped[str]
    year: Mapped[int | None]
    library: Mapped[str] = mapped_column(default="Default")
    original_language: Mapped[str | None] = mapped_column(default=None)
    imdb_id: Mapped[str | None] = mapped_column(default=None)
    tagline: Mapped[str | None] = mapped_column(default=None)
    genres = mapped_column(ARRAY(String), nullable=True, default=list)
    runtime: Mapped[int | None] = mapped_column(default=None)
    release_date: Mapped[str | None] = mapped_column(default=None)
    metadata_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )


class MediaFileMixin:
    """
    Mixin for common media file fields used by both Movie files and Episode files.
    """

    file_path_suffix: Mapped[str]
    quality: Mapped[Quality]
    torrent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(column="torrent.id", ondelete="SET NULL"),
    )
