from datetime import datetime

from pydantic import BaseModel

from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult


class RatedMedia(BaseModel):
    """A library movie or show the user rated, with what's needed to use it
    as a recommendation seed."""

    name: str
    metadata_provider: str
    external_id: int
    imdb_id: str | None
    genres: list[str]
    score: int
    rated_at: datetime


class PersonalRecommendation(BaseModel):
    """A movie or show recommended to the current user."""

    media: MetaDataProviderSearchResult
    """`added`, `id` and `slug` are set when it's already in the library."""
    because_of: str
    """The title the user rated or watched that contributed most to this
    recommendation."""
    because_score: int | None
    """The user's rating of `because_of`, or None if they only watched it."""
