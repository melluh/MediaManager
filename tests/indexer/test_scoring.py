import pytest

from media_manager.indexer.classification import classify_release
from media_manager.indexer.config import (
    BitrateBand,
    HdrLadderConfig,
    IndexerConfig,
    LanguagePolicyConfig,
    ReleaseGroupTier,
    ScoringRuleSet,
    SlotCondition,
    SlotDefinition,
    TitleScoringRule,
)
from media_manager.indexer.schemas import IndexerQueryResult
from media_manager.indexer.scoring import slot_and_score_results
from media_manager.indexer.title_parsing import derive_quality
from media_manager.movies.schemas import Movie
from media_manager.tv.schemas import Episode, Season, Show


def size_for_mbps(mbps: float, runtime_minutes: int) -> int:
    return int((mbps * 1_000_000 * runtime_minutes * 60) / 8)


def make_result(title: str, size_gb: float | None = None, *, size: int | None = None, seeders: int = 50, usenet: bool = False, flags: list[str] | None = None) -> IndexerQueryResult:
    return IndexerQueryResult(
        title=title,
        download_url="magnet:?xt=urn:btih:x",
        seeders=seeders,
        flags=flags or [],
        size=size if size is not None else int((size_gb or 1) * 1024**3),
        usenet=usenet,
        age=0,
        indexer="test",
        quality=derive_quality(title),
        attributes=classify_release(title),
    )


DEFAULT_SLOTS = [
    SlotDefinition(
        name="4k_remux",
        label="4K Remux",
        conditions=[
            SlotCondition(attribute="resolution", operator="eq", value="2160p"),
            SlotCondition(attribute="source", operator="eq", value="remux"),
        ],
        bitrate=BitrateBand(min_mbps=50, preferred_mbps=70, max_mbps=90),
    ),
    SlotDefinition(
        name="4k_encode",
        label="4K Encode",
        conditions=[
            SlotCondition(attribute="resolution", operator="eq", value="2160p"),
            SlotCondition(attribute="source", operator="not_in", value=["remux"]),
            SlotCondition(attribute="codec", operator="in", value=["h265", "av1"]),
        ],
        bitrate=BitrateBand(min_mbps=10, preferred_mbps=17, max_mbps=25),
    ),
    SlotDefinition(
        name="1080p_encode",
        label="1080p Encode",
        conditions=[
            SlotCondition(attribute="resolution", operator="eq", value="1080p"),
            SlotCondition(attribute="source", operator="not_in", value=["remux"]),
            SlotCondition(attribute="codec", operator="in", value=["h264", "h265", "av1"]),
        ],
        bitrate=BitrateBand(min_mbps=4, preferred_mbps=8, max_mbps=15),
    ),
]


def make_config(**overrides) -> IndexerConfig:
    defaults = {
        "slots": DEFAULT_SLOTS,
        "hdr_ladder": HdrLadderConfig(),
        "release_group_tiers": [ReleaseGroupTier(tier=1, groups=["FraMeSToR"])],
        "language_policy": LanguagePolicyConfig(allowed_variants_default=[]),
        "min_seeders": 5,
        "legacy_rule_score_clamp": 20,
    }
    defaults.update(overrides)
    return IndexerConfig(**defaults)


@pytest.fixture
def patch_indexer_config(monkeypatch):
    def _patch(config: IndexerConfig):
        class _FakeMediaManagerConfig:
            indexers = config

        # scoring.py and utils.py (evaluate_indexer_query_result, invoked
        # from within slot_and_score_results) each import their own
        # MediaManagerConfig binding - both need patching.
        monkeypatch.setattr(
            "media_manager.indexer.scoring.MediaManagerConfig",
            lambda: _FakeMediaManagerConfig(),
        )
        monkeypatch.setattr(
            "media_manager.indexer.utils.MediaManagerConfig",
            lambda: _FakeMediaManagerConfig(),
        )

    return _patch


@pytest.fixture
def movie() -> Movie:
    return Movie(
        name="Test Movie",
        overview="",
        year=2024,
        external_id=1,
        metadata_provider="tmdb",
        runtime=120,
        library="Default",
    )


def test_slot_assignment_and_within_slot_ranking(patch_indexer_config, movie):
    patch_indexer_config(make_config())

    remux = make_result(
        "Movie.2024.2160p.UHD.BluRay.REMUX.HDR10.HEVC.Atmos.7.1-FraMeSToR",
        size_for_mbps(70, 120) / 1024**3,
        seeders=100,
    )
    web_dl = make_result(
        "Movie.2024.2160p.WEB-DL.DV.HDR10.DDP5.1.H.265-FLUX",
        size_for_mbps(17, 120) / 1024**3,
        seeders=80,
    )
    webrip = make_result(
        "Movie.2024.2160p.WEBRip.DDP5.1.x265-CasStudio",
        size_for_mbps(15, 120) / 1024**3,
        seeders=20,
    )

    out = slot_and_score_results(results=[remux, web_dl, webrip], media=movie, is_tv=False)

    by_title = {r.title: r for r in out}
    assert by_title[remux.title].slot_name == "4k_remux"
    assert by_title[web_dl.title].slot_name == "4k_encode"
    assert by_title[webrip.title].slot_name == "4k_encode"
    # WEB-DL must outrank WEBRip within the same 4k_encode slot.
    assert by_title[web_dl.title].score > by_title[webrip.title].score


def test_codec_preference_within_shared_encode_slot(patch_indexer_config, movie):
    # h264 and h265 1080p encodes share a single "1080p_encode" slot (no
    # separate slot per codec) - x265 must still outrank x264 within it via
    # the codec scoring factor.
    patch_indexer_config(make_config())
    h264 = make_result(
        "Movie.2024.1080p.WEB-DL.x264-GRP", size_for_mbps(8, 120) / 1024**3, seeders=50
    )
    h265 = make_result(
        "Movie2.2024.1080p.WEB-DL.x265-GRP", size_for_mbps(8, 120) / 1024**3, seeders=50
    )
    out = slot_and_score_results(results=[h264, h265], media=movie, is_tv=False)
    by_title = {r.title: r for r in out}
    assert by_title[h264.title].slot_name == "1080p_encode"
    assert by_title[h265.title].slot_name == "1080p_encode"
    assert by_title[h265.title].score > by_title[h264.title].score


def test_unmatched_slot_result_is_unslotted_not_dropped(patch_indexer_config, movie):
    patch_indexer_config(make_config())
    # XviD at 1080p matches none of the configured slots (the 1080p_encode
    # slot only covers h264/h265/av1) - it must still appear in the output,
    # just without a slot, and still get a real (non-zero) score from the
    # slot-independent factors (seeders, etc).
    result = make_result(
        "Movie.2024.1080p.WEB-DL.XviD-GRP", size_for_mbps(7, 120) / 1024**3
    )
    out = slot_and_score_results(results=[result], media=movie, is_tv=False)
    assert len(out) == 1
    assert out[0].slot_name is None
    assert out[0].score > 0


def test_bitrate_hard_reject_within_slot(patch_indexer_config, movie):
    patch_indexer_config(make_config())
    fake = make_result(
        "Movie.2024.1080p.WEB-DL.x265-FAKEGROUP", size_for_mbps(40, 120) / 1024**3
    )
    real = make_result(
        "Movie.2024.1080p.WEB-DL.x265-REALGROUP", size_for_mbps(7, 120) / 1024**3
    )
    out = slot_and_score_results(results=[fake, real], media=movie, is_tv=False)
    titles = {r.title for r in out}
    assert real.title in titles
    assert fake.title not in titles


def test_bitrate_band_inclusive_edges(patch_indexer_config, movie):
    patch_indexer_config(make_config())
    at_min = make_result("Movie.2024.1080p.WEB-DL.x265-GRP", size_for_mbps(4, 120) / 1024**3)
    at_max = make_result("Movie2.2024.1080p.WEB-DL.x265-GRP", size_for_mbps(15, 120) / 1024**3)
    just_below = make_result(
        "Movie3.2024.1080p.WEB-DL.x265-GRP", size_for_mbps(3.9, 120) / 1024**3
    )
    out = slot_and_score_results(
        results=[at_min, at_max, just_below], media=movie, is_tv=False
    )
    titles = {r.title for r in out}
    assert at_min.title in titles
    assert at_max.title in titles
    assert just_below.title not in titles


def test_unknown_runtime_never_rejects_on_bitrate(patch_indexer_config):
    patch_indexer_config(make_config())
    movie_no_runtime = Movie(
        name="Test Movie",
        overview="",
        year=2024,
        external_id=2,
        metadata_provider="tmdb",
        runtime=None,
        library="Default",
    )
    result = make_result(
        "Movie.2024.1080p.WEB-DL.x265-GRP", size_for_mbps(999, 120) / 1024**3
    )
    out = slot_and_score_results(results=[result], media=movie_no_runtime, is_tv=False)
    assert len(out) == 1
    assert out[0].effective_mbps is None
    assert out[0].slot_name == "1080p_encode"


def make_episode_count_callback(show: Show):
    # Mirrors media_manager.tv.service.get_all_available_torrents_for_a_season's
    # episode_count_for_torrent callback: single-episode releases divide by
    # their own episode count, season packs fall back to the season total.
    def episode_count_for_torrent(result: IndexerQueryResult) -> int | None:
        if result.episode:
            return len(result.episode)
        count = sum(len(s.episodes) for s in show.seasons if s.number in result.season)
        return count or None

    return episode_count_for_torrent


def test_single_episode_bitrate_divisor_not_whole_season(patch_indexer_config):
    patch_indexer_config(make_config())
    show = Show(
        name="Test Show",
        overview="",
        year=2024,
        external_id=5,
        metadata_provider="tmdb",
        runtime=30,
        library="Default",
        seasons=[
            Season(
                number=1,
                name="Season 1",
                overview="",
                external_id=11,
                episodes=[
                    Episode(number=i, external_id=200 + i, title=f"Ep {i}")
                    for i in range(1, 11)
                ],
            )
        ],
    )
    # A single 30-minute episode at 7 Mbps - dividing by the whole season's
    # 10 episodes (300 min) would incorrectly compute ~0.7 Mbps and get
    # bitrate-rejected from the 1080p_encode slot (band: 4-15 Mbps).
    result = make_result(
        "Test.Show.2024.S01E05.1080p.WEB-DL.x265-GRP", size_for_mbps(7, 30) / 1024**3
    )
    result.season = [1]
    result.episode = [5]

    out = slot_and_score_results(
        results=[result],
        media=show,
        is_tv=True,
        episode_count_for_torrent=make_episode_count_callback(show),
    )
    assert len(out) == 1
    assert out[0].effective_mbps == pytest.approx(7, abs=0.1)
    assert out[0].slot_name == "1080p_encode"


def test_season_pack_bitrate_divisor(patch_indexer_config):
    patch_indexer_config(make_config())
    show = Show(
        name="Test Show",
        overview="",
        year=2024,
        external_id=3,
        metadata_provider="tmdb",
        runtime=30,
        library="Default",
        seasons=[
            Season(
                number=1,
                name="Season 1",
                overview="",
                external_id=10,
                episodes=[
                    Episode(number=i, external_id=100 + i, title=f"Ep {i}")
                    for i in range(1, 11)
                ],
            )
        ],
    )
    # 10 episodes * 30 min = 300 min total runtime for the season pack.
    result = make_result(
        "Test.Show.2024.S01.1080p.WEB-DL.x265-GRP", size_for_mbps(7, 300) / 1024**3
    )
    result.season = [1]

    out = slot_and_score_results(
        results=[result],
        media=show,
        is_tv=True,
        episode_count_for_torrent=make_episode_count_callback(show),
    )
    assert len(out) == 1
    assert out[0].effective_mbps == pytest.approx(7, abs=0.1)
    assert out[0].slot_name == "1080p_encode"


def test_season_pack_missing_episode_count_skips_bitrate(patch_indexer_config):
    patch_indexer_config(make_config())
    show = Show(
        name="Test Show",
        overview="",
        year=2024,
        external_id=4,
        metadata_provider="tmdb",
        runtime=30,
        library="Default",
        seasons=[],
    )
    result = make_result(
        "Test.Show.2024.S01.1080p.WEB-DL.x265-GRP", size_for_mbps(999, 300) / 1024**3
    )
    result.season = [1]

    out = slot_and_score_results(
        results=[result],
        media=show,
        is_tv=True,
        episode_count_for_torrent=make_episode_count_callback(show),
    )
    assert len(out) == 1
    assert out[0].effective_mbps is None


def test_legacy_rule_negative_sum_still_hard_rejects(patch_indexer_config, movie):
    config = make_config(
        title_scoring_rules=[
            TitleScoringRule(name="avoid_cam", keywords=["cam"], score_modifier=-10000),
            TitleScoringRule(name="prefer_h265", keywords=["h265"], score_modifier=100),
        ],
        scoring_rule_sets=[
            ScoringRuleSet(
                name="default",
                libraries=["ALL_MOVIES"],
                rule_names=["avoid_cam", "prefer_h265"],
            )
        ],
    )
    patch_indexer_config(config)
    # Matches both rules: -10000 + 100 = -9900, must still net-reject even
    # though a positive rule also matched.
    result = make_result("Movie.2024.CAM.1080p.h265-GRP", size_for_mbps(7, 120) / 1024**3)
    out = slot_and_score_results(results=[result], media=movie, is_tv=False)
    assert out == []


def test_legacy_rule_positive_sum_is_clamped(patch_indexer_config, movie):
    config = make_config(
        title_scoring_rules=[
            TitleScoringRule(name="prefer_h265", keywords=["h265"], score_modifier=300),
        ],
        scoring_rule_sets=[
            ScoringRuleSet(name="default", libraries=["ALL_MOVIES"], rule_names=["prefer_h265"])
        ],
        legacy_rule_score_clamp=20,
    )
    patch_indexer_config(config)
    result = make_result(
        "Movie.2024.1080p.WEB-DL.h265-GRP", size_for_mbps(7, 120) / 1024**3
    )
    out = slot_and_score_results(results=[result], media=movie, is_tv=False)
    assert len(out) == 1
    legacy_entries = [e for e in out[0].score_breakdown if e.rule_name == "legacy_rules"]
    assert legacy_entries == [legacy_entries[0]]
    assert legacy_entries[0].score_modifier == 20


def test_empty_legacy_config_contributes_zero(patch_indexer_config, movie):
    patch_indexer_config(make_config(title_scoring_rules=[], scoring_rule_sets=[]))
    result = make_result(
        "Movie.2024.1080p.WEB-DL.h265-GRP", size_for_mbps(7, 120) / 1024**3
    )
    out = slot_and_score_results(results=[result], media=movie, is_tv=False)
    assert len(out) == 1
    assert all(e.rule_name != "legacy_rules" for e in out[0].score_breakdown)


def test_seeder_hard_filter(patch_indexer_config, movie):
    patch_indexer_config(make_config(min_seeders=10))
    low_seeders = make_result(
        "Movie.2024.1080p.WEB-DL.h265-GRP", size_for_mbps(7, 120) / 1024**3, seeders=3
    )
    out = slot_and_score_results(results=[low_seeders], media=movie, is_tv=False)
    assert out == []


def test_seeder_hard_filter_skipped_for_usenet(patch_indexer_config, movie):
    patch_indexer_config(make_config(min_seeders=10))
    usenet_result = make_result(
        "Movie.2024.1080p.WEB-DL.h265-GRP",
        size_for_mbps(7, 120) / 1024**3,
        seeders=0,
        usenet=True,
    )
    out = slot_and_score_results(results=[usenet_result], media=movie, is_tv=False)
    assert len(out) == 1


def test_language_variant_hard_filter_and_opt_in(patch_indexer_config, movie):
    patch_indexer_config(make_config(language_policy=LanguagePolicyConfig(allowed_variants_default=[])))
    multi = make_result(
        "Movie.2024.MULTI.1080p.WEB-DL.h265-GRP", size_for_mbps(7, 120) / 1024**3
    )

    rejected = slot_and_score_results(results=[multi], media=movie, is_tv=False)
    assert rejected == []

    allowed = slot_and_score_results(
        results=[multi], media=movie, is_tv=False, allow_language_variants=["multi"]
    )
    assert len(allowed) == 1


def test_search_query_override_bypass_returns_unslotted():
    # Mirrors the movies/tv service bypass path: raw search() results are
    # returned without ever calling slot_and_score_results. This test just
    # documents/protects the invariant that unscored results have no slot
    # fields set by default.
    result = make_result("Movie.2024.1080p.WEB-DL.h265-GRP")
    assert result.slot_name is None
    assert result.slot_index is None
    assert result.effective_mbps is None
