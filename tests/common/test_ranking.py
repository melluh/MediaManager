from dataclasses import dataclass

from media_manager.common.ranking import derive_title_fields, rank_entries

DEFAULT_SCORE_CUTOFF = 60.0
DEFAULT_CANDIDATE_LIMIT = 300


@dataclass(slots=True)
class _Candidate:
    """
    Minimal local stand-in for a rankable candidate, deliberately NOT
    `titleIndex.index.IndexEntry` - proves `rank_entries` is genuinely
    generic (structural typing via `Rankable`), not accidentally coupled to
    the title-index's own dataclass.
    """

    label: str
    normalized: str
    acronym_full: str
    acronym_no_article: str
    popularity_pct: float


def _build(titles_with_popularity_pct: list[tuple[str, float]]) -> list[_Candidate]:
    return [
        _Candidate(label=title, normalized=normalized, acronym_full=acronym_full, acronym_no_article=acronym_no_article, popularity_pct=popularity_pct)
        for title, popularity_pct in titles_with_popularity_pct
        for normalized, acronym_full, acronym_no_article in [derive_title_fields(title)]
    ]


def _rank(titles_with_popularity_pct: list[tuple[str, float]], query: str):
    entries = _build(titles_with_popularity_pct)
    normalized_titles = [entry.normalized for entry in entries]
    return rank_entries(
        entries,
        normalized_titles,
        query,
        score_cutoff=DEFAULT_SCORE_CUTOFF,
        candidate_limit=DEFAULT_CANDIDATE_LIMIT,
    )


def test_derive_title_fields_strips_leading_article_for_acronym() -> None:
    normalized, acronym_full, acronym_no_article = derive_title_fields("The Lord of the Rings")

    assert normalized == "the lord of the rings"
    assert acronym_full == "tlotr"
    assert acronym_no_article == "lotr"


def test_typo_query_still_ranks_correct_title_top() -> None:
    ranked = _rank([("Jurassic Park", 50.0), ("Inception", 50.0)], "Jurasic Park")

    assert ranked[0].entry.label == "Jurassic Park"
    assert ranked[0].is_structural is False


def test_acronym_without_article_matches_full_title() -> None:
    titles = [("The Lord of the Rings", 50.0), ("Inception", 50.0)]
    ranked = _rank(titles, "lotr")

    assert ranked[0].entry.label == "The Lord of the Rings"
    assert ranked[0].is_structural is True


def test_structural_prefix_match_outranks_plain_fuzzy_substring_match() -> None:
    titles = [("Costar", 90.0), ("Star Trek", 10.0)]
    ranked = _rank(titles, "star")

    assert ranked[0].entry.label == "Star Trek"
    assert ranked[0].is_structural is True
    assert ranked[1].is_structural is False


def test_popularity_bonus_breaks_ties_between_equally_fuzzy_matches() -> None:
    titles = [("Twins", 10.0), ("Twins", 90.0)]
    ranked = _rank(titles, "twins")

    assert ranked[0].entry.popularity_pct == 90.0


def test_score_cutoff_excludes_irrelevant_entries() -> None:
    ranked = _rank([("The Matrix", 50.0)], "xyzzy plugh")

    assert ranked == []


def test_popular_exact_word_title_outranks_obscure_full_exact_match() -> None:
    titles = [("Matrix", 5.0), ("The Matrix", 95.0)]
    ranked = _rank(titles, "matrix")

    assert ranked[0].entry.label == "The Matrix"


def test_acronym_match_outranks_unrelated_generic_prefix_match() -> None:
    titles = [("Gotham", 60.0), ("Game of Thrones", 90.0)]
    ranked = _rank(titles, "got")

    assert ranked[0].entry.label == "Game of Thrones"


def test_constant_popularity_pct_ties_break_by_input_order_when_fuzzy_scores_tie() -> None:
    # token_set_ratio scores "Star" and "Star Trek" identically against
    # query "star" (both are token-set supersets containing the query), so
    # with an identical (library-style) popularity_pct there's no further
    # signal to break the tie - order falls back to input order (Python's
    # sort is stable). That's fine: either is a reasonable "did you mean"
    # outcome, not a case of an irrelevant match winning.
    titles = [("Star", 50.0), ("Star Trek", 50.0)]
    ranked = _rank(titles, "star")

    assert {ranked[0].entry.label, ranked[1].entry.label} == {"Star", "Star Trek"}
    assert ranked[0].tier_score == ranked[1].tier_score


def test_popularity_pct_discriminates_within_structural_tier_when_it_differs() -> None:
    titles = [("Star", 10.0), ("Star Trek", 90.0)]
    ranked = _rank(titles, "star")

    assert ranked[0].entry.label == "Star Trek"


def test_long_title_short_query_structural_match_is_not_silently_dropped() -> None:
    # Regression: a genuine title-prefix match with a raw text-similarity
    # score far below score_cutoff (a short query against a much longer
    # official title) must still be found and correctly classified as
    # structural - it used to be silently dropped entirely, since structural
    # status was only ever checked for candidates that had already survived
    # score_cutoff via the fuzzy-only path.
    titles = [
        (
            "Borat: Cultural Learnings of America for Make Benefit Glorious Nation of Kazakhstan",
            50.0,
        ),
        ("Bratz", 90.0),
    ]
    ranked = _rank(titles, "Borat")

    assert ranked[0].entry.label.startswith("Borat")
    assert ranked[0].is_structural is True


def test_trailing_phrase_match_found_via_token_set_ratio() -> None:
    # Regression: a query matching only a *trailing* phrase of a longer
    # title (not a prefix) must still be found and ranked above shorter,
    # unrelated titles that happen to share more raw characters with the
    # query - plain character-overlap ratio scored those higher and crowded
    # the correct match out entirely. token_set_ratio scores the genuine
    # match 100 (the query's words are a full subset of the title's words)
    # vs. 76-86 for the unrelated "*Street" titles, comfortably outweighing
    # a realistic popularity gap (the correct match need not be the most
    # popular of the bunch, just not rock-bottom).
    titles = [("The End of Oak Street", 50.0), ("Wall Street", 70.0), ("E Street", 70.0)]
    ranked = _rank(titles, "Oak Street")

    assert ranked[0].entry.label == "The End of Oak Street"
    assert ranked[0].is_structural is False


def test_a_later_incidental_token_match_is_not_treated_as_structural() -> None:
    # Regression: "star" is a prefix of "Starring", a later word in this
    # title, but the title itself doesn't start with "star" - this must not
    # be treated as structural (which would let it dominate purely on its
    # own popularity), unlike a genuine query-vs-title-opening match. In
    # practice the match is so tenuous (a 4-letter query against one word of
    # a 6-word, otherwise-unrelated title) that it doesn't even clear
    # score_cutoff on its own - it's correctly absent entirely, not just
    # ranked below the real match.
    titles = [
        ("Star Trek", 10.0),
        ("The Tonight Show Starring Jimmy Fallon", 99.0),
    ]
    ranked = _rank(titles, "star")

    assert ranked[0].entry.label == "Star Trek"
    assert ranked[0].is_structural is True
    assert not any("Starring" in e.entry.label for e in ranked)


def test_a_long_unrelated_query_does_not_match_titles_that_are_one_of_its_words() -> None:
    # Regression: token_set_ratio alone would score "Here" 100 against this
    # query (its one token is a full subset of the query's many tokens),
    # even though "Here" has essentially nothing to do with the query as a
    # whole. Inclusion in the fuzzy-only tier is gated by plain `ratio`
    # (length-sensitive, ~22 for this pair) before token_set_ratio is ever
    # used for ranking - so no match should survive here at all.
    titles = [("Here", 90.0), ("Search", 90.0), ("So Weird", 90.0)]
    ranked = _rank(titles, "very weird search query goes here")

    assert ranked == []
