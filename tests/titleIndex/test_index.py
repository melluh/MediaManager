from media_manager.common.ranking import derive_title_fields
from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.index import IndexEntry, rank_entries

TITLES = [
    "The Matrix",
    "The Lord of the Rings",
    "Jurassic Park",
    "Inception",
    "The Dark Knight",
]


def _build_entries(titles_with_popularity_pct: list[tuple[str, float]]) -> list[IndexEntry]:
    entries = []
    for position, (title, popularity_pct) in enumerate(titles_with_popularity_pct):
        normalized, acronym_full, acronym_no_article = derive_title_fields(title)
        entries.append(
            IndexEntry(
                id=position,
                title=title,
                normalized=normalized,
                popularity=popularity_pct,
                media_type=MediaType.movie,
                acronym_full=acronym_full,
                acronym_no_article=acronym_no_article,
                popularity_pct=popularity_pct,
            )
        )
    return entries


def _rank(titles_with_popularity_pct: list[tuple[str, float]], query: str) -> list[IndexEntry]:
    entries = _build_entries(titles_with_popularity_pct)
    normalized_titles = [entry.normalized for entry in entries]
    return rank_entries(entries, normalized_titles, query, TitleIndexConfig())


def test_typo_query_still_ranks_correct_title_top() -> None:
    ranked = _rank([(title, 50.0) for title in TITLES], "Jurasic Park")

    assert ranked[0].title == "Jurassic Park"


def test_acronym_without_article_matches_full_title() -> None:
    ranked = _rank([(title, 50.0) for title in TITLES], "lotr")

    assert ranked[0].title == "The Lord of the Rings"
    # `acronym_full` alone (with the leading article) would be "tlotr" and
    # miss this query entirely - confirms the no-article variant is doing
    # the matching.
    entry = next(e for e in ranked if e.title == "The Lord of the Rings")
    assert entry.acronym_full == "tlotr"
    assert entry.acronym_no_article == "lotr"


def test_structural_prefix_match_outranks_plain_fuzzy_substring_match() -> None:
    # "Star Trek" has "star" as a whole-token prefix (structural tier).
    # "Costar" merely contains "star" as a non-prefix substring, so it's
    # ranked in the fuzzy-only tier - which always loses to the structural
    # tier, regardless of raw fuzzy score or popularity.
    titles = [("Costar", 90.0), ("Star Trek", 10.0)]
    ranked = _rank(titles, "star")

    assert ranked[0].title == "Star Trek"


def test_popularity_breaks_ties_between_equally_fuzzy_matches() -> None:
    # Identical title (and therefore identical fuzzy score and prefix bonus)
    # listed with the less popular one first, to prove popularity_pct - not
    # input order - decides the winner.
    titles = [("Twins", 10.0), ("Twins", 90.0)]
    ranked = _rank(titles, "twins")

    assert ranked[0].id == 1
    assert ranked[0].popularity_pct == 90.0


def test_score_cutoff_excludes_irrelevant_entries() -> None:
    ranked = _rank([(title, 50.0) for title in TITLES], "xyzzy plugh")

    assert ranked == []


def test_popular_exact_word_title_outranks_obscure_full_exact_match() -> None:
    # Regression test: an earlier single-formula version of this ranking let
    # a small, obscure show titled exactly "Matrix" outrank the far more
    # popular "The Matrix", because raw fuzzy score (100 for the exact
    # match) dominated the formula regardless of the popularity gap. Both
    # are structural (token-prefix) matches for "matrix", so this is really
    # a same-tier popularity comparison.
    titles = [("Matrix", 5.0), ("The Matrix", 95.0)]
    ranked = _rank(titles, "matrix")

    assert ranked[0].title == "The Matrix"


def test_acronym_match_outranks_unrelated_generic_prefix_match() -> None:
    # "got" is both a literal prefix of "Gotham" and the acronym of "Game of
    # Thrones". The acronym match must not lose out just because it isn't
    # a plain-text prefix.
    titles = [("Gotham", 60.0), ("Game of Thrones", 90.0)]
    ranked = _rank(titles, "got")

    assert ranked[0].title == "Game of Thrones"
