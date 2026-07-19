from enum import Enum

from pydantic import BaseModel

from media_manager.movies.schemas import MovieId
from media_manager.tv.schemas import ShowId


class MediaType(str, Enum):
    """
    The media types a metadata provider (or the local search index) can
    return. Add a member here when a new media type becomes searchable.
    """

    movie = "movie"
    tv = "tv"


class MetaDataProviderSearchResult(BaseModel):
    poster_path: str | None
    overview: str | None
    name: str
    external_id: int
    year: int | None
    metadata_provider: str
    media_type: MediaType
    added: bool
    vote_average: float | None = None
    original_language: str | None = None
    id: MovieId | ShowId | None = None  # Internal ID if already added
