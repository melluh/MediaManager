from media_manager.indexer.title_parsing import (
    derive_episode,
    derive_quality,
    derive_season,
)
from media_manager.torrent.models import Quality


def test_derive_quality_tiers():
    assert derive_quality("Movie.2024.2160p.WEB-DL.x265-GRP") == Quality.uhd
    assert derive_quality("Movie.2024.4K.WEB-DL.x265-GRP") == Quality.uhd
    assert derive_quality("Movie.2024.1080p.WEB-DL.x264-GRP") == Quality.fullhd
    assert derive_quality("Movie.2024.720p.WEB-DL.x264-GRP") == Quality.hd
    assert derive_quality("Movie.2024.480p.WEB-DL.x264-GRP") == Quality.sd
    assert derive_quality("Movie.2024.WEB-DL.x264-GRP") == Quality.unknown


def test_derive_season_single_episode():
    assert derive_season("Show.S01E02.1080p.WEB-DL-GRP") == [1]


def test_derive_season_range_pack():
    assert derive_season("Show.S01-S03.1080p.WEB-DL-GRP") == [1, 2, 3]


def test_derive_season_pack():
    assert derive_season("Show.S02.1080p.WEB-DL-GRP") == [2]


def test_derive_season_word_form():
    # Note: the "Season N" form requires a literal space (the pre-existing
    # regex uses \s*, which does not match the "." scene-name separator).
    assert derive_season("Show.Season 4.1080p.WEB-DL-GRP") == [4]


def test_derive_season_none():
    assert derive_season("Movie.2024.1080p.WEB-DL-GRP") == []


def test_derive_episode_single():
    assert derive_episode("Show.S01E05.1080p.WEB-DL-GRP") == [5]


def test_derive_episode_range():
    # Note: the range form only matches without a second "E" prefix
    # (S01E01-03), matching the pre-existing regex's behavior.
    assert derive_episode("Show.S01E01-03.1080p.WEB-DL-GRP") == [1, 2, 3]


def test_derive_episode_pack_has_no_episode():
    assert derive_episode("Show.S01.1080p.WEB-DL-GRP") == []
