import uuid
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from media_manager.torrent.models import Quality


class BaseMedia(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid.uuid4)
    name: str
    overview: str
    year: int | None
    external_id: int
    metadata_provider: str
    library: str = "Default"
    original_language: str | None = None
    imdb_id: str | None = None
    tagline: str | None = None
    genres: list[str] = Field(default_factory=list)
    runtime: int | None = None
    release_date: str | None = None
    metadata_updated_at: datetime | None = None

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


class PublicMediaFile(BaseMediaFile):
    downloaded: bool = False
    imported: bool = False
