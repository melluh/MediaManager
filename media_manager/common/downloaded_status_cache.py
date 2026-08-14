from enum import StrEnum
from uuid import UUID


class DownloadedMediaType(StrEnum):
    movie = "movie"
    episode = "episode"


_cache: dict[tuple[DownloadedMediaType, UUID], bool] = {}


def get_cached_downloaded(media_type: DownloadedMediaType, media_id: UUID) -> bool | None:
    """
    Returns the last-scanned downloaded status for a piece of media, or
    None if it hasn't been scanned yet (e.g. briefly after startup, before
    the first scheduled scan has completed). Callers should fall back to a
    cheap DB-only signal for None rather than treating it as False.
    """
    return _cache.get((media_type, media_id))


def set_cached_downloaded_statuses(
    media_type: DownloadedMediaType, statuses: dict[UUID, bool]
) -> None:
    for media_id, downloaded in statuses.items():
        _cache[(media_type, media_id)] = downloaded
