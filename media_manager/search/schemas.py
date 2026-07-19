from uuid import UUID

from pydantic import BaseModel

from media_manager.metadataProvider.schemas import MediaType

__all__ = ["MediaType", "SearchResult"]


class SearchResult(BaseModel):
    id: UUID
    media_type: MediaType
    name: str
    overview: str
    year: int | None
