from pydantic_settings import BaseSettings


class SearchConfig(BaseSettings):
    max_results: int = 8
    """Overall result cap (not per media type) for both plain library search
    and the merged library + not-in-library combined search."""

    score_cutoff: float = 60.0
    """Minimum rapidfuzz `ratio` score for a library fuzzy-only candidate to
    be considered at all - same semantics as `TitleIndexConfig.score_cutoff`."""

    library_match_bonus: float = 50.0
    """Flat value passed through the shared ranking formula's
    `popularity_pct` slot for every library candidate (see
    `media_manager.common.ranking.Rankable`). Since it's identical across
    all library candidates, it never affects their ordering *relative to
    each other* - only rapidfuzz's fuzzy score does that (via the shared
    formula's small tiebreak weight). Any value works equally well for that;
    50 is just a neutral midpoint.

    This does NOT decide whether library results outrank not-in-library
    ones - that used to be its job, and it didn't hold up in practice: TMDB
    popularity percentiles over a ~150k-title pool are generously
    distributed enough (many ordinary, moderately-known titles land in the
    90th+ percentile) that no fixed bonus reliably kept genuine in-library
    matches on top without being fragile (only a bonus at the theoretical
    maximum, 100, ever consistently won, and even then only by the barest
    margin against a title at the 99.9th percentile). Library-vs-not-library
    precedence is now decided explicitly by `SearchService.combined_search`,
    which sorts on `(is_structural, in_library, tier_score)` - library
    always wins ties of the same match quality, full stop."""
