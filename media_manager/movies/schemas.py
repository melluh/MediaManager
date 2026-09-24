import typing
import uuid
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from media_manager.common.schemas import (
    BaseMedia,
    BaseMediaFile,
    PublicMediaFile,
    Quality,
    SubtitleLanguage,
)
from media_manager.torrent.schemas import TorrentId, TorrentStatus

MovieId = typing.NewType("MovieId", UUID)


class Movie(BaseMedia):
    id: MovieId = Field(default_factory=lambda: MovieId(uuid.uuid4()))


class MovieListItem(Movie):
    """Movie plus the file-derived fields needed to filter the library list
    (downloaded status, probed quality, subtitle languages) without a
    per-movie query."""

    downloaded: bool = False
    quality: Quality | None = None
    """Best quality probed across the movie's files; None when it has no
    probed file."""
    subtitle_languages: list[SubtitleLanguage] | None = None
    """Distinct subtitle languages across the movie's probed files. Empty when
    its files have no subtitles; None when it has no probed file."""


class MovieFile(BaseMediaFile):
    movie_id: MovieId


class PublicMovieFile(MovieFile, PublicMediaFile):
    pass


class MovieDownload(BaseModel):
    """A torrent's link to the movie it was downloaded for."""

    model_config = ConfigDict(from_attributes=True)

    torrent_id: TorrentId
    movie_id: MovieId
    file_path_suffix: str


class MovieTorrent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    torrent_id: TorrentId
    torrent_title: str
    status: TorrentStatus
    slot: str | None = None
    imported: bool
    cancelled: bool = False
    file_path_suffix: str
    usenet: bool


class PublicMovie(Movie):
    slug: str
    downloaded: bool = False
    torrents: list[MovieTorrent] = Field(default_factory=list)


class RichMovieTorrent(BaseModel):
    movie_id: MovieId
    name: str
    slug: str
    year: int | None
    metadata_provider: str
    torrents: list[MovieTorrent]
