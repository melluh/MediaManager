import uuid

from media_manager.common.schemas import SubtitleLanguage
from media_manager.common.subtitle_language_cache import (
    SubtitleMediaType,
    get_cached_subtitle_languages,
    set_cached_subtitle_languages,
    update_cached_subtitle_languages,
)

_ENGLISH = SubtitleLanguage(code="eng", name="English")


def test_full_scan_replaces_previous_entries():
    stale, kept, no_subtitles, no_file = (uuid.uuid4() for _ in range(4))
    set_cached_subtitle_languages(SubtitleMediaType.movie, {stale: [_ENGLISH]})

    set_cached_subtitle_languages(
        SubtitleMediaType.movie,
        {kept: [_ENGLISH], no_subtitles: [], no_file: None},
    )

    assert get_cached_subtitle_languages(SubtitleMediaType.movie, stale) is None
    assert get_cached_subtitle_languages(SubtitleMediaType.movie, kept) == [_ENGLISH]
    assert get_cached_subtitle_languages(SubtitleMediaType.movie, no_subtitles) == []
    assert get_cached_subtitle_languages(SubtitleMediaType.movie, no_file) is None


def test_single_update_sets_and_clears_one_entry():
    movie_id, other_id = uuid.uuid4(), uuid.uuid4()
    set_cached_subtitle_languages(SubtitleMediaType.movie, {other_id: []})

    update_cached_subtitle_languages(SubtitleMediaType.movie, movie_id, [_ENGLISH])
    assert get_cached_subtitle_languages(SubtitleMediaType.movie, movie_id) == [_ENGLISH]

    update_cached_subtitle_languages(SubtitleMediaType.movie, movie_id, None)
    assert get_cached_subtitle_languages(SubtitleMediaType.movie, movie_id) is None
    # Other entries are untouched by a single-item update.
    assert get_cached_subtitle_languages(SubtitleMediaType.movie, other_id) == []
