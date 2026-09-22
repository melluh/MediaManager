from pydantic_settings import BaseSettings


class TitleIndexConfig(BaseSettings):
    max_entries: int = 150_000
    """Combined movie+tv entries kept in the on-disk title index, bounded by
    popularity via a max-heap while streaming the daily export. Keeps memory
    and per-query fuzzy-scoring cost bounded regardless of the raw export's
    size (~1-1.5M rows, most of them near-zero popularity)."""

    score_cutoff: float = 60.0
    """Minimum rapidfuzz `ratio` score for a *non-structural* (fuzzy-only)
    candidate to be considered at all - structural (title-prefix/acronym)
    candidates are found exhaustively, independent of this cutoff. Plain
    `ratio`, not `token_set_ratio` (used only to rank whatever survives this
    gate) - length-sensitive so a short title can't pass just because it's
    one word of a much longer, unrelated query. See
    `media_manager.common.ranking.rank_entries`."""

    candidate_limit: int = 300
    """How many fuzzy-only candidates rapidfuzz considers per query, on top
    of the exhaustively-found structural ones. Needs to be generous: for a
    short, common query there can easily be more than a few dozen
    near-matches, and rapidfuzz's `limit` truncates by raw fuzzy score
    alone - too low a limit can truncate away the actually-best fuzzy match
    entirely. Verified against a real ~150k-entry index that 300 is
    comfortably past the point where results stop changing, while staying
    fast enough for interactive use (~70-105ms: `process.extract` scans
    with the cheaper plain `ratio` scorer for inclusion, and the pricier
    `token_set_ratio` only runs on whatever survives that gate - see
    `media_manager.common.ranking.rank_entries`'s docstring)."""

    max_results: int = 8
    """Suggestions returned per query, after in-library filtering."""

    stale_after_hours: float = 36.0
    """How old the on-disk index may get before startup kicks an immediate
    refresh instead of waiting for the next daily cron tick."""
