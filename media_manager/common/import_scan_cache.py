from datetime import UTC, datetime
from enum import StrEnum

from media_manager.schemas import MediaImportSuggestion


class ImportScanMediaType(StrEnum):
    movie = "movie"
    tv = "tv"


class _ImportScanCacheEntry:
    def __init__(self, suggestions: list[MediaImportSuggestion]) -> None:
        self.suggestions = suggestions
        self.scanned_at = datetime.now(UTC)


_cache: dict[ImportScanMediaType, _ImportScanCacheEntry] = {}


def get_cached_importable_media(
    media_type: ImportScanMediaType,
) -> list[MediaImportSuggestion]:
    """
    Returns the last scanned list of importable media for the given type, or
    an empty list if no scan has completed yet (e.g. briefly after startup).
    """
    entry = _cache.get(media_type)
    return entry.suggestions if entry else []


def set_cached_importable_media(
    media_type: ImportScanMediaType, suggestions: list[MediaImportSuggestion]
) -> None:
    _cache[media_type] = _ImportScanCacheEntry(suggestions)
