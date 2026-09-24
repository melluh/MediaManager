"""
The subtitle languages found on disk for each piece of media, for library
list filters. Finding them means probing every file with ffprobe, far too
slow for a list request, so a scheduled scan fills this cache and the list
endpoint only reads it.
"""

from enum import StrEnum
from uuid import UUID

from media_manager.common.schemas import SubtitleLanguage


class SubtitleMediaType(StrEnum):
    movie = "movie"


_cache: dict[SubtitleMediaType, dict[UUID, list[SubtitleLanguage]]] = {}


def get_cached_subtitle_languages(
    media_type: SubtitleMediaType, media_id: UUID
) -> list[SubtitleLanguage] | None:
    """
    The distinct subtitle languages across a piece of media's files on disk.
    An empty list means its files have no subtitles at all; None means there
    is no file on disk, or the first scan hasn't completed yet.
    """
    return _cache.get(media_type, {}).get(media_id)


def set_cached_subtitle_languages(
    media_type: SubtitleMediaType,
    languages: dict[UUID, list[SubtitleLanguage] | None],
) -> None:
    """
    Replaces the whole cache for a media type with a full scan's results, so
    media deleted or emptied since the last scan drop out rather than lingering.
    """
    _cache[media_type] = {
        media_id: media_languages
        for media_id, media_languages in languages.items()
        if media_languages is not None
    }


def update_cached_subtitle_languages(
    media_type: SubtitleMediaType,
    media_id: UUID,
    languages: list[SubtitleLanguage] | None,
) -> None:
    """Refreshes a single entry, e.g. after one item's files were just probed."""
    entries = _cache.setdefault(media_type, {})
    if languages is None:
        entries.pop(media_id, None)
    else:
        entries[media_id] = languages
