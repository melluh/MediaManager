"""
Recommendations are scored from the TMDB "also liked" lists of titles the
user rated or watched (seeds), weighted by their opinion of each seed.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from media_manager.metadataProvider.schemas import (
    ExternalPosterImage,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.recommendation.schemas import RatedMedia
from media_manager.recommendation.service import (
    MAX_PER_REASON,
    MIN_RECENCY_FACTOR,
    WATCHED_WEIGHT,
    Seed,
    build_seeds,
    genre_profile,
    rank_candidates,
    recency_factor,
)

NOW = datetime(2026, 10, 15, tzinfo=UTC)


def _result(
    tmdb_id: int,
    genres: list[str] | None = None,
    poster: bool = True,
    vote_average: float | None = None,
) -> MetaDataProviderSearchResult:
    return MetaDataProviderSearchResult(
        poster_images=[ExternalPosterImage(url="p")] if poster else [],
        overview=None,
        name=f"Title {tmdb_id}",
        external_id=tmdb_id,
        year=2000,
        metadata_provider="tmdb",
        media_type=MediaType.movie,
        added=False,
        genres=genres or [],
        vote_average=vote_average,
    )


def _rated(
    external_id: int,
    score: int,
    metadata_provider: str = "tmdb",
    imdb_id: str | None = None,
    genres: list[str] | None = None,
    age: timedelta = timedelta(),
) -> RatedMedia:
    return RatedMedia(
        name=f"Rated {external_id}",
        metadata_provider=metadata_provider,
        external_id=external_id,
        imdb_id=imdb_id,
        genres=genres or [],
        score=score,
        rated_at=NOW - age,
    )


def _watched(
    tmdb_id: int | None, imdb_id: str | None = None, age: timedelta = timedelta()
) -> SimpleNamespace:
    return SimpleNamespace(
        name=f"Watched {tmdb_id}",
        imdb_id=imdb_id,
        tmdb_id=tmdb_id,
        tvdb_id=None,
        last_played_at=NOW - age,
    )


def _seed(tmdb_id: int, weight: float, score: int | None = None) -> Seed:
    return Seed(tmdb_id=tmdb_id, name=f"Seed {tmdb_id}", weight=weight, score=score)


def _ids(recommendations: list) -> list[int]:
    return [r.media.external_id for r in recommendations]


# -----------------------------------------------------------------------------
# SEEDS
# -----------------------------------------------------------------------------


def test_ratings_and_unrated_watches_become_seeds() -> None:
    seeds, known = build_seeds(
        [_rated(1, 2), _rated(2, -1)], [_watched(1), _watched(3)], NOW
    )

    by_id = {seed.tmdb_id: seed for seed in seeds}
    # A rating overrides the watch of the same title.
    assert by_id[1].weight == 2
    assert by_id[1].score == 2
    assert by_id[2].weight == -1
    assert by_id[3].weight == WATCHED_WEIGHT
    assert by_id[3].score is None
    assert known == {1, 2, 3}


def test_neutral_rating_is_known_but_not_a_seed() -> None:
    seeds, known = build_seeds([_rated(1, 0)], [_watched(1)], NOW)

    assert seeds == []
    assert known == {1}


def test_non_tmdb_library_titles_get_their_tmdb_id_from_watches() -> None:
    seeds, known = build_seeds(
        [
            _rated(81189, 2, metadata_provider="tvdb", imdb_id="tt0903747"),
            _rated(999, 2, metadata_provider="tvdb"),
        ],
        [_watched(1396, imdb_id="tt0903747")],
        NOW,
    )

    assert [(seed.tmdb_id, seed.score) for seed in seeds] == [(1396, 2)]
    assert known == {1396}


def test_old_opinions_count_less_but_never_nothing() -> None:
    assert recency_factor(NOW, NOW) == 1
    assert recency_factor(NOW - timedelta(days=365), NOW) == 0.5
    assert recency_factor(NOW - timedelta(days=3650), NOW) == MIN_RECENCY_FACTOR
    assert recency_factor(None, NOW) == MIN_RECENCY_FACTOR


def test_genre_profile_leans_towards_rated_genres() -> None:
    profile = genre_profile(
        [
            _rated(1, 2, genres=["Drama"]),
            _rated(2, 2, genres=["Drama", "Horror"]),
            _rated(3, -2, genres=["Horror"]),
        ]
    )

    assert profile["Drama"] > 0
    assert profile["Horror"] == 0


# -----------------------------------------------------------------------------
# RANKING
# -----------------------------------------------------------------------------


def test_titles_recommended_by_more_and_higher_seeds_rank_first() -> None:
    lists = {
        1: [_result(10), _result(11), _result(12)],
        2: [_result(12)],
    }

    ranked = rank_candidates([_seed(1, 2), _seed(2, 1)], lists, {}, set())

    assert _ids(ranked) == [12, 10, 11]


def test_disliked_seeds_push_their_list_down() -> None:
    lists = {1: [_result(10), _result(11)], 2: [_result(10)]}

    ranked = rank_candidates([_seed(1, 1), _seed(2, -2)], lists, {}, set())

    assert _ids(ranked) == [11]


def test_titles_only_disliked_seeds_lead_to_are_not_recommended() -> None:
    ranked = rank_candidates(
        [_seed(1, -1)], {1: [_result(10, vote_average=10)]}, {}, set()
    )

    assert ranked == []


def test_excluded_and_posterless_titles_are_skipped() -> None:
    lists = {1: [_result(10), _result(11, poster=False), _result(12)]}

    ranked = rank_candidates([_seed(1, 1)], lists, {}, {10})

    assert _ids(ranked) == [12]


def test_genre_taste_breaks_ties() -> None:
    lists = {
        1: [_result(10, genres=["Horror"])],
        2: [_result(11, genres=["Drama"])],
    }

    ranked = rank_candidates(
        [_seed(1, 1), _seed(2, 1)], lists, {"Drama": 0.5, "Horror": -0.5}, set()
    )

    assert _ids(ranked) == [11, 10]


def test_credits_the_seed_that_contributed_most() -> None:
    lists = {1: [_result(20), _result(10)], 2: [_result(10)]}

    ranked = rank_candidates(
        [_seed(1, 1, score=1), _seed(2, 2, score=2)], lists, {}, set()
    )

    by_id = {r.media.external_id: r for r in ranked}
    assert by_id[10].because_of == "Seed 2"
    assert by_id[10].because_score == 2


def test_one_seed_cannot_fill_the_whole_list() -> None:
    lists = {
        1: [_result(i) for i in range(100, 110)],
        2: [_result(200)],
    }

    ranked = rank_candidates([_seed(1, 2), _seed(2, 0.5)], lists, {}, set())

    assert _ids(ranked) == [*[100, 101, 102, 103][:MAX_PER_REASON], 200]
