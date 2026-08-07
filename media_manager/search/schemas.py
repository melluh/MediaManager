from uuid import UUID

from media_manager.common.schemas import BaseMedia
from media_manager.metadataProvider.schemas import MediaType

__all__ = ["MediaType", "SearchResult"]


class SearchResult(BaseMedia):
    id: UUID
    slug: str  # Make slug non-nullable (because SearchResult is only used for in-library results, which always have a slug)
    media_type: MediaType
