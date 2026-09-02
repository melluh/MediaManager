import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from media_manager.torrent.models import Quality

# Increase to force immediate metadata refresh (regardless of configured metadata refresh interval).
# Useful when metadata fetching logic changes or a new field is stored from metadata.
CURRENT_METADATA_VERSION = 3


class BaseMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    slug: str | None = None
    directory_name: str | None = None
    overview: str
    year: int | None
    external_id: int
    metadata_provider: str
    library: str = "Default"
    original_language: str | None = None
    imdb_id: str | None = None
    trailer_url: str | None = None
    tagline: str | None = None
    genres: list[str] = Field(default_factory=list)
    runtime: int | None = None
    release_date: str | None = None
    metadata_updated_at: datetime | None = None
    metadata_version: int = CURRENT_METADATA_VERSION
    images: dict[str, str] = Field(default_factory=dict) # Image type (e.g. "poster", "backdrop") -> static file path

    @field_validator("genres", mode="before")
    @classmethod
    def _default_genres_to_empty_list(cls, v: list[str] | None) -> list[str]:
        # Rows created before the genres column existed have it as NULL.
        return v or []


class BaseMediaFile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quality: Quality
    torrent_id: UUID | None = None
    file_path_suffix: str
    relative_path: str | None = None


class MediaFileDetails(BaseModel):
    """
    What the file on disk itself says about the media, as opposed to what the
    database row claims. Populated by probing the file; every field is
    optional because probing is best-effort.
    """

    size_bytes: int | None = None
    probed_quality: Quality | None = None
    """Quality measured from the video stream, which can differ from the recorded `quality`."""
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    audio_channels: int | None = None
    container: str | None = None


class PublicMediaFile(BaseMediaFile):
    downloaded: bool = False
    imported: bool = False
    file_path: str = ""
    """Path of the file on disk, relative to the media type's library root.

    Falls back to the expected path (without extension) when the file has not
    been imported yet.
    """
    exists_on_disk: bool = False
    """Whether a file was actually found at `file_path`."""
    details: MediaFileDetails | None = None
    """File facts read from disk; None when the file isn't there."""
