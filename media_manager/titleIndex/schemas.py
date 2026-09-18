from pydantic import BaseModel

from media_manager.metadataProvider.schemas import MediaType


class TitleSuggestion(BaseModel):
    """
    A fast, typo-tolerant autocomplete suggestion sourced from TMDB's daily
    ID export, for media not yet in the library.

    Deliberately minimal (no poster/year): the daily export only carries id,
    title and popularity. Selecting a suggestion is expected to trigger a
    live provider search/detail call for full information.
    """

    id: int
    title: str
    media_type: MediaType
    popularity: float
