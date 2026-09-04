import typing
import uuid
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from media_manager.common.schemas import BaseMedia, BaseMediaFile, PublicMediaFile
from media_manager.torrent.models import Quality
from media_manager.torrent.schemas import TorrentId, TorrentStatus

MovieId = typing.NewType("MovieId", UUID)


class Movie(BaseMedia):
    id: MovieId = Field(default_factory=lambda: MovieId(uuid.uuid4()))


class MovieListItem(Movie):
    """Movie plus the file-derived fields needed to filter the library list
    (downloaded status, download quality) without a per-movie query."""

    downloaded: bool = False
    quality: Quality | None = None


class MovieFile(BaseMediaFile):
    movie_id: MovieId


class PublicMovieFile(MovieFile, PublicMediaFile):
    pass


class MovieTorrent(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    torrent_id: TorrentId
    torrent_title: str
    status: TorrentStatus
    quality: Quality
    imported: bool
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
