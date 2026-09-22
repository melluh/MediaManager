from dataclasses import dataclass
from typing import Protocol

from rapidfuzz import fuzz, process

from media_manager.common.import_match import normalize_title

_ARTICLES = ("the", "a", "an")
_ACRONYM_PROXY_SCORE = 90.0


class Rankable(Protocol):
    """
    Structural shape `rank_entries` needs from a candidate, regardless of
    where it came from (a TMDB title-index row, a library row, ...).
    `popularity_pct` doesn't have to be a real popularity - library
    candidates pass a flat constant through this same slot (see
    `media_manager.search.service`) purely so the shared formula still has
    something to break ties on *within* a pool; cross-pool precedence
    between library and not-in-library results is decided separately, by
    the caller that merges two pools' outputs (see
    `SearchService.combined_search`), not by this value competing
    numerically against a real popularity percentile.
    """

    normalized: str
    acronym_full: str
    acronym_no_article: str
    popularity_pct: float


@dataclass(slots=True)
class ScoredEntry[T]:
    entry: T
    is_structural: bool
    tier_score: float


def _acronym(tokens: list[str]) -> str:
    return "".join(token[0] for token in tokens if token)


def derive_title_fields(title: str) -> tuple[str, str, str]:
    """
    Normalizes `title` and derives its two acronym variants: initials of
    every token (`acronym_full`), and the same with one leading article
    (the/a/an) stripped first (`acronym_no_article`). This is the concrete
    mechanism behind abbreviation tolerance - "lotr" matching "The Lord of
    the Rings", "got" matching "Game of Thrones" - which plain edit-distance
    fuzzy matching alone can't bridge.

    :param title: The raw title to derive matching fields for.
    :return: (normalized, acronym_full, acronym_no_article).
    """
    normalized = normalize_title(title)
    tokens = normalized.split(" ") if normalized else []
    acronym_full = _acronym(tokens)
    no_article_tokens = tokens[1:] if tokens and tokens[0] in _ARTICLES else tokens
    acronym_no_article = _acronym(no_article_tokens)
    return normalized, acronym_full, acronym_no_article


def _is_title_prefix(normalized_title: str, normalized_query: str) -> bool:
    """
    Whether `normalized_query` is a prefix of `normalized_title`, allowing
    one leading article (the/a/an) in the title to be skipped first - same
    pattern as `acronym_no_article`. This is what lets "matrix" match "The
    Matrix" (skip "the", then "matrix" is an exact prefix of what's left)
    while still excluding "star" matching "The Tonight Show Starring Jimmy
    Fallon" (after skipping "the", the remainder starts with "tonight", not
    "star").

    Deliberately NOT "does any token anywhere in the title start with the
    query" (an earlier version of this check) - that's too permissive and
    lets an incidental, late, unrelated word in an otherwise long title
    dominate the structural tier purely on that title's own popularity,
    regardless of how tenuous the actual match is.
    """
    if normalized_title.startswith(normalized_query):
        return True
    tokens = normalized_title.split(" ")
    if tokens and tokens[0] in _ARTICLES:
        return " ".join(tokens[1:]).startswith(normalized_query)
    return False


def rank_entries[T: Rankable](
    entries: list[T],
    normalized_titles: list[str],
    query: str,
    *,
    score_cutoff: float,
    candidate_limit: int,
) -> list[ScoredEntry[T]]:
    """
    Pure, pool-agnostic ranking step - no filesystem/DB/lock involved, so
    it's directly testable, and generic enough to rank a TMDB title-index
    pool and a library pool with identical logic (see
    `media_manager.titleIndex.index` and `media_manager.search.service`).

    Splits candidates into two tiers rather than blending every signal into
    one formula (validated against a real ~150k-entry TMDB index - an
    earlier single-formula version let a merely-exact-but-obscure title
    outrank a hugely more popular prefix match):

    - "Structural" matches - the query is a title-prefix (see
      `_is_title_prefix`) or matches an acronym - already have relevance
      established by that relationship, so `popularity_pct` decides which
      one the user most likely means; the fuzzy score only breaks near-ties
      (e.g. an exact match vs. a longer prefix).
    - Everything else is a typo/near-miss (or a query that matches only a
      *trailing* phrase of a longer title, e.g. "oak street" against "The
      End of Oak Street" - not a prefix, so this is the only tier that ever
      finds it) with no structural relationship to lean on, so closeness of
      the text match must dominate, with `popularity_pct` only breaking
      ties between similarly-close matches.

    Structural status is determined *exhaustively*, independent of
    `score_cutoff`: a genuine title-prefix or acronym match must never be
    silently dropped just because its overall text-similarity score is low
    on its own - e.g. a short query against a much longer official title
    ("borat" vs. "Borat: Cultural Learnings of America for Make Benefit
    Glorious Nation of Kazakhstan" scores ~12% on raw text similarity
    despite being an exact, obvious match) would otherwise never even reach
    the point where its structural status gets checked.

    `entries` is returned scored (not just reordered) so a caller can merge
    two independently-ranked pools - critical when one pool is large enough
    that `candidate_limit` would otherwise silently truncate the other
    pool's candidates out if they were naively concatenated before ranking.

    :param entries: Candidates to rank; each must expose `normalized`,
        `acronym_full`, `acronym_no_article`, `popularity_pct`.
    :param normalized_titles: `entries[i].normalized`, parallel list -
        passed separately since rapidfuzz's `process.extract` wants a flat
        string sequence, not attribute access per candidate.
    :param query: Raw (not yet normalized) user query.
    :param score_cutoff: Minimum rapidfuzz `ratio` score for a non-structural
        (fuzzy-only) candidate to be considered at all - deliberately the
        length-sensitive plain-ratio score, not the more lenient
        `token_set_ratio` used for ranking survivors (see below), so a
        short, unrelated title can't pass just because it happens to be one
        word of a much longer, otherwise-irrelevant query.
    :param candidate_limit: How many fuzzy candidates rapidfuzz considers.
        Pass a value comfortably above the largest plausible match count for
        common queries - too low silently truncates the actual best fuzzy
        match out before popularity ever gets a say. Structural candidates
        are unaffected by this limit (found exhaustively).
    """
    normalized_query = normalize_title(query)
    if not normalized_query or not entries:
        return []

    is_acronym_query = normalized_query.isalpha() and 2 <= len(normalized_query) <= 6
    structural_indices: set[int] = set()
    scored: dict[int, float] = {}

    for index, entry in enumerate(entries):
        is_prefix_hit = _is_title_prefix(entry.normalized, normalized_query)
        is_acronym_hit = is_acronym_query and normalized_query in (
            entry.acronym_full,
            entry.acronym_no_article,
        )
        if not (is_prefix_hit or is_acronym_hit):
            continue
        structural_indices.add(index)
        scored[index] = (
            fuzz.token_set_ratio(normalized_query, entry.normalized)
            if is_prefix_hit
            else _ACRONYM_PROXY_SCORE
        )

    # Two different scorers doing two different jobs here, deliberately:
    #
    # - Plain `ratio` decides *inclusion* (via score_cutoff). It penalizes
    #   length mismatch symmetrically, which is exactly what's needed to
    #   reject a short, unrelated title that merely happens to be one word
    #   of a much longer query ("Here" scores 100 on token_set_ratio against
    #   "very weird search query goes here" - a full token-set subset - but
    #   only ~22 on plain ratio, correctly below cutoff).
    # - token_set_ratio decides *ranking* among whatever survives that gate.
    #   A query whose words are a genuine subset of the title's words - "oak
    #   street" against "The End of Oak Street" - scores far higher under
    #   token_set_ratio (~100) than under plain ratio (~64, which several
    #   shorter, unrelated titles sharing surface characters with the query
    #   - "K Street", "E Street" - also cleared and outscored on).
    #
    # Both directions of length mismatch are covered this way: a title much
    # longer than the query (Oak Street) still needs to clear the ratio
    # gate (it does, comfortably, when the match is real), and a title much
    # shorter than the query (the garbage-query case) gets rejected by that
    # same gate even though token_set_ratio alone would have let it through.
    matches = process.extract(
        normalized_query,
        normalized_titles,
        scorer=fuzz.ratio,
        score_cutoff=score_cutoff,
        limit=candidate_limit,
    )
    for _choice, _score, index in matches:
        if index in scored:
            continue  # already scored via the structural path above
        scored[index] = fuzz.token_set_ratio(normalized_query, normalized_titles[index])

    ranked: list[ScoredEntry[T]] = []
    for index, fuzzy_score in scored.items():
        entry = entries[index]
        is_structural = index in structural_indices
        tier_score = (
            entry.popularity_pct + 0.05 * fuzzy_score
            if is_structural
            else 0.75 * fuzzy_score + 0.25 * entry.popularity_pct
        )
        ranked.append(
            ScoredEntry(entry=entry, is_structural=is_structural, tier_score=tier_score)
        )

    ranked.sort(key=lambda scored_entry: (scored_entry.is_structural, scored_entry.tier_score), reverse=True)
    return ranked
