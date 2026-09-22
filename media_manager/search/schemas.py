from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from media_manager.common.schemas import BaseMedia
from media_manager.metadataProvider.schemas import MediaType

__all__ = ["CombinedSearchResult", "MediaType", "SearchResult"]


class SearchResult(BaseMedia):
    id: UUID
    slug: str  # Make slug non-nullable (because SearchResult is only used for in-library results, which always have a slug)
    media_type: MediaType


class CombinedSearchResult(BaseModel):
    """
    One pre-merged, pre-ranked search result - either an already-in-library
    item or a not-yet-added suggestion from the title index, distinguished
    by `in_library`. Mirrors the existing dual-purpose shape of
    `MetaDataProviderSearchResult` (`added` + optional `id`/`slug`),
    inverted around library membership. See
    `SearchService.combined_search`.
    """

    in_library: bool
    media_type: MediaType
    name: str

    # Populated when in_library is True.
    id: UUID | None = None
    slug: str | None = None
    year: int | None = None
    runtime: int | None = None
    genres: list[str] = Field(default_factory=list)
    images: dict[str, str] = Field(default_factory=dict)
    metadata_updated_at: datetime | None = None

    # Populated when in_library is False.
    external_id: int | None = None
    popularity: float | None = None
