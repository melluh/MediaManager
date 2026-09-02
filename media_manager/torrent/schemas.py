import typing
import uuid
from datetime import datetime
from enum import Enum, StrEnum

from pydantic import BaseModel, ConfigDict, Field

TorrentId = typing.NewType("TorrentId", uuid.UUID)


class Quality(Enum):
    uhd = 1
    fullhd = 2
    hd = 3
    sd = 4
    unknown = 5


class QualityStrings(Enum):
    uhd = "4K"
    fullhd = "1080p"
    hd = "720p"
    sd = "400p"
    unknown = "unknown"


class TorrentStatus(Enum):
    finished = 1
    downloading = 2
    error = 3
    unknown = 4


class ImportErrorKind(StrEnum):
    """
    Structured tag for a `Torrent.import_error`, letting the API offer a
    targeted resolution flow for failure types it knows how to fix. Left
    unset for failures that have no such flow (yet).
    """

    multiple_video_files = "multiple_video_files"


class Torrent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: TorrentId = Field(default_factory=lambda: TorrentId(uuid.uuid4()))
    status: TorrentStatus
    title: str
    quality: Quality
    imported: bool
    import_error: str | None = None
    """Set when the last automatic import attempt failed; cleared on success or manual resolution."""
    import_error_kind: ImportErrorKind | None = None
    """Structured kind of `import_error`, if recognized; drives which manual-resolution endpoint applies."""
    hash: str
    usenet: bool = False
    initiated_by_user_id: uuid.UUID | None = None
    initiated_at: datetime | None = None
    indexer: str | None = None
    comments: str | None = None
    """Link to the indexer's detail page for this release, if any."""


class DownloadState(StrEnum):
    """
    Fine-grained, client-neutral download-client state, distinct from the
    persisted TorrentStatus. Live-only (never stored) so new client-specific
    states can be added without a migration.
    """

    downloading = "downloading"
    queued = "queued"
    stalled = "stalled"
    checking = "checking"
    stopped = "stopped"
    seeding = "seeding"
    finished = "finished"
    error = "error"
    unknown = "unknown"


class DownloadProgress(BaseModel):
    state: DownloadState
    progress: float
    """Percentage complete, 0-100."""
    total_bytes: int | None = None
    downloaded_bytes: int | None = None
    download_speed_bytes_per_second: int | None = None
    eta_seconds: int | None = None
    seeders: int | None = None
    leechers: int | None = None


class TorrentMedia(BaseModel):
    """
    Minimal, client-neutral summary of the movie/show a torrent belongs to -
    just enough for the dashboard to render a poster and link. Deliberately
    doesn't import Movie/Show schemas (which import from here), so it's built
    from whichever one applies at the call site.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str | None = None
    year: int | None
    is_show: bool
    metadata_updated_at: datetime | None = None
    images: dict[str, str] = Field(default_factory=dict)


class TorrentWithProgress(Torrent):
    download_progress: DownloadProgress | None = None
    """Live progress from the download client, if it supports reporting one."""
    media: TorrentMedia | None = None
    """The movie/show this torrent belongs to, if one has been linked yet."""


class TorrentImportCandidate(BaseModel):
    """A video file found in a torrent's download directory, offered up for manual import resolution."""

    relative_path: str
    """Path relative to the torrent's download directory; the identifier passed back to resolve the import."""
    file_name: str
    size_bytes: int
    quality: Quality
    duration_seconds: int | None = None
    """Playback duration, if it could be determined by probing the file."""


_DOWNLOAD_STATE_TO_TORRENT_STATUS: dict[DownloadState, TorrentStatus] = {
    DownloadState.downloading: TorrentStatus.downloading,
    DownloadState.stalled: TorrentStatus.downloading,
    DownloadState.queued: TorrentStatus.downloading,
    DownloadState.checking: TorrentStatus.downloading,
    DownloadState.stopped: TorrentStatus.downloading,
    DownloadState.seeding: TorrentStatus.finished,
    DownloadState.finished: TorrentStatus.finished,
    DownloadState.error: TorrentStatus.error,
    DownloadState.unknown: TorrentStatus.unknown,
}


def download_state_to_torrent_status(state: DownloadState) -> TorrentStatus:
    """Collapse a fine-grained DownloadState into the coarser, persisted TorrentStatus."""
    return _DOWNLOAD_STATE_TO_TORRENT_STATUS.get(state, TorrentStatus.unknown)
