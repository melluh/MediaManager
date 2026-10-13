from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class LibraryStats(BaseModel):
    movie_count: int
    show_count: int
    episode_count: int


DiskUsageCategoryKey = Literal["movies", "tv", "images", "other"]


class DiskUsageCategory(BaseModel):
    key: DiskUsageCategoryKey
    label: str
    bytes: int


class DiskUsageEntry(BaseModel):
    names: list[str]
    """One or more configured library/path names sharing this filesystem,
    e.g. ["Movies", "Anime"]."""
    paths: list[str]
    total_bytes: int
    used_bytes: int
    free_bytes: int
    categories: list[DiskUsageCategory] = []
    """What the used space on this filesystem is taken up by. Categories
    with nothing on this filesystem are left out, except "other", which is
    always last and holds whatever MediaManager didn't put there. Empty when
    the filesystem is unavailable."""
    available: bool = True
    """False if the path could not be statted (missing/unmounted); the byte
    fields are 0 in that case."""


class LargestMediaItem(BaseModel):
    id: UUID
    slug: str
    name: str
    year: int | None
    media_type: Literal["movie", "show"]
    bytes: int


class DiskUsageStats(BaseModel):
    entries: list[DiskUsageEntry]
    largest_media: list[LargestMediaItem] = []
    """The movies and the shows taking up the most space (up to 20 of
    each), mixed, largest first."""
