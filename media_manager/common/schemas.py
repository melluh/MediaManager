import uuid
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from media_manager.torrent.models import Quality

# Increase to force immediate metadata refresh (regardless of configured metadata refresh interval).
# Useful when metadata fetching logic changes or a new field is stored from metadata.
CURRENT_METADATA_VERSION = 5


class MediaAddedByUser(BaseModel):
    """The user a media item is attributed to, as shown alongside `created_at`."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str | None = None


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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    """When this media item was added to the library."""
    added_by_user_id: UUID | None = None
    """Raw FK, settable when creating a media item. Read back via `added_by`."""
    added_by: MediaAddedByUser | None = None
    """The user who added this media item, if known and not since deleted."""
    images: dict[str, str] = Field(default_factory=dict) # Image type (e.g. "poster", "backdrop") -> static file path
    image_source_paths: dict[str, str] = Field(default_factory=dict)
    """Image type -> provider path/URL last used to download that image, so a
    metadata refresh can tell whether it actually changed. Populated at read
    time from the `media_image` table, same as `images` is from disk."""

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


class SubtitleLanguage(BaseModel):
    """
    A subtitle's language, normalized across the vocabularies it can be
    reported in (ISO 639-1/639-2B/639-2T codes, IETF tags, English names) -
    see `media_manager.common.languages.parse_language`.
    """

    code: str
    """ISO 639-3 code (e.g. "eng", "deu", "por"), or "und" when unknown.
    Stable across sources, so this is what to filter and group by."""
    region: str | None = None
    """ISO 3166-1 alpha-2 country, when the source named one (e.g. "BR" for
    "pt-BR")."""
    name: str
    """Human-readable name, e.g. "English", "Portuguese (Brazil)", "Unknown"."""


class SubtitleTrack(BaseModel):
    """
    A subtitle track discovered for a media file - either embedded in the
    video container (found by ffprobe) or a sidecar file sitting next to it.

    Distinct from `media_manager.indexer.classification.SubtitleInfo`, which
    describes subtitles *claimed* by a release's title before anything is
    downloaded; this describes what was actually found on disk.

    All string fields are treated as untrusted: they originate from a
    downloaded file's own metadata or filename, so values are sanitized
    (length-capped, allowlisted) before being placed here rather than passed
    through raw.
    """

    language: SubtitleLanguage
    """Normalized language, whichever code the source used (an embedded
    stream's "ger" and a sidecar's "de" both become "deu"). Always set: a
    missing or unrecognized code is the explicit Unknown language."""
    source: Literal["embedded", "sidecar"]
    forced: bool = False
    hearing_impaired: bool = False
    codec: str | None = None
    """Embedded: ffprobe's codec_name (e.g. "subrip"). Sidecar: the file's
    extension without the dot (e.g. "srt")."""


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
    subtitles: list[SubtitleTrack] = Field(default_factory=list)
    """Subtitle tracks found for this file: embedded streams plus sidecar
    files matching the same filename stem. Empty list means none were found,
    which is distinct from `None` fields elsewhere in this model that mean
    "couldn't be determined"."""


class WatchUrl(BaseModel):
    """Response for the movie/show "watch-url" endpoint, fetched separately
    from the media's main details so a slow or unconfigured media server
    never blocks the movie/show page from loading."""

    url: str | None = None
    media_server_name: str | None = None
    """Display name of the media server the url points to (e.g. "Jellyfin"),
    for labeling a "Watch on <name>" button. None whenever `url` is None."""


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
