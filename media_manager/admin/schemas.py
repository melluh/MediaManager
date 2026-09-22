from pydantic import BaseModel


class LibraryStats(BaseModel):
    movie_count: int
    show_count: int
    episode_count: int


class DiskUsageEntry(BaseModel):
    names: list[str]
    """One or more configured library/path names sharing this filesystem,
    e.g. ["Movies", "Anime"]."""
    paths: list[str]
    total_bytes: int
    used_bytes: int
    free_bytes: int
    available: bool = True
    """False if the path could not be statted (missing/unmounted); the byte
    fields are 0 in that case."""


class DiskUsageStats(BaseModel):
    entries: list[DiskUsageEntry]
