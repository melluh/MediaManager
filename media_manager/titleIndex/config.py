from pydantic_settings import BaseSettings


class TitleIndexConfig(BaseSettings):
    max_entries: int = 150_000
    """Combined movie+tv entries kept in the on-disk title index, bounded by
    popularity via a max-heap while streaming the daily export. Keeps memory
    and per-query fuzzy-scoring cost bounded regardless of the raw export's
    size (~1-1.5M rows, most of them near-zero popularity)."""

    score_cutoff: float = 60.0
    """Minimum rapidfuzz WRatio score for a fuzzy candidate to be considered
    at all."""

    candidate_limit: int = 300
    """How many fuzzy candidates rapidfuzz considers per query. Needs to be
    generous (not just `max_results` + headroom for in-library filtering):
    for a short, common query (e.g. "star") there can easily be more than a
    few dozen exact/near-exact prefix matches, and rapidfuzz's `limit` truncates
    by raw fuzzy score alone, before popularity ever enters the ranking - too
    low a limit can truncate away the actually-popular match entirely.
    Verified against a real ~150k-entry index that 300 is comfortably past
    the point where results stop changing, while staying fast (~40ms)."""

    max_results: int = 8
    """Suggestions returned per query, after in-library filtering."""

    stale_after_hours: float = 36.0
    """How old the on-disk index may get before startup kicks an immediate
    refresh instead of waiting for the next daily cron tick."""
