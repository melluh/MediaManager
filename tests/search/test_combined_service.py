import asyncio
import gzip
import json
from pathlib import Path

from media_manager.search.config import SearchConfig
from media_manager.search.schemas import MediaType
from media_manager.search.service import SearchService
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.service import TitleSuggestionService
from tests.search.test_service import _media, _StubRepository


def _write_title_index(path: Path, rows: list[dict]) -> None:
    """
    `popularity_pct` is derived from each row's *position* in this list
    (rank, not the raw "p" value - see IndexEntry._derive_entries), so
    fixtures here order rows most-popular-first, exactly like the real
    on-disk artifact.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def _filler_rows(count: int, media_type: str = "movie") -> list[dict]:
    return [
        {"id": 1000 + i, "t": f"Filler Title {i}", "p": 1.0, "m": media_type}
        for i in range(count)
    ]


def _build_service(
    tmp_path: Path,
    *,
    library_rows: list,
    title_index_rows: list[dict],
) -> SearchService:
    _write_title_index(tmp_path / "title_index.ndjson.gz", title_index_rows)
    empty_repo = _StubRepository([])
    title_suggestion_service = TitleSuggestionService(
        repositories={MediaType.movie: empty_repo, MediaType.tv: empty_repo},
        directory=tmp_path,
        config=TitleIndexConfig(),
    )
    return SearchService(
        repositories={
            MediaType.movie: _StubRepository(library_rows),
            MediaType.tv: _StubRepository([]),
        },
        title_suggestion_service=title_suggestion_service,
        config=SearchConfig(max_results=5),
    )


def test_library_always_wins_over_not_in_library_within_the_same_structural_tier(
    tmp_path: Path,
) -> None:
    # Regression for a real user-reported bug: an earlier design tried to
    # make in-library results outrank not-in-library ones via a flat
    # "in-library bonus" competing numerically against the not-in-library
    # pool's real popularity percentile. That didn't hold up in practice -
    # TMDB popularity percentiles over a ~150k-title pool are generously
    # distributed enough that ordinary, moderately-known titles routinely
    # land in the 90th+ percentile, so even a near-maximum bonus lost to a
    # title at the 99.9th percentile. combined_search now sorts on
    # (is_structural, in_library, tier_score) - library always wins ties of
    # the same match quality, unconditionally, regardless of how popular the
    # not-in-library competitor is.
    library = [_media("Star", external_id=1)]
    # Placed at rank 0 of a large pool -> popularity_pct == 100, the
    # theoretical maximum - even this must not surface above the library.
    title_index_rows = [{"id": 2, "t": "Star Trek", "p": 500.0, "m": "tv"}, *_filler_rows(50)]

    service = _build_service(tmp_path, library_rows=library, title_index_rows=title_index_rows)
    results = asyncio.run(service.combined_search("star"))

    assert results[0].in_library is True
    assert results[0].name == "Star"


def test_library_always_wins_over_not_in_library_within_the_fuzzy_only_tier(
    tmp_path: Path,
) -> None:
    # Same invariant as above, one tier down: a library typo/near-miss match
    # (fuzzy-only, no clean prefix/acronym relative to the typo'd query)
    # must still outrank a not-in-library fuzzy-only match, however popular.
    # "Jurassic Park" (correctly spelled) doesn't start with the typo'd
    # query, so this is genuinely fuzzy-only for the library side too - not
    # a redundant re-test of the structural-tier guarantee above.
    library = [_media("Jurassic Park", external_id=1)]
    title_index_rows = [
        {"id": 2, "t": "Jurassic World", "p": 500.0, "m": "movie"},
        *_filler_rows(50),
    ]

    service = _build_service(tmp_path, library_rows=library, title_index_rows=title_index_rows)
    results = asyncio.run(service.combined_search("jurasic park"))

    assert results[0].in_library is True
    assert results[0].name == "Jurassic Park"


def test_not_in_library_structural_match_beats_library_fuzzy_only_match(
    tmp_path: Path,
) -> None:
    # Named, accepted consequence of keeping is_structural as the primary
    # sort key across the merge (see SearchService.combined_search's
    # docstring): a typo'd query for a library item with no clean
    # prefix/acronym hit can be outranked by an unrelated not-in-library
    # structural match. Pinned here so a future change to this behavior is
    # deliberate.
    library = [_media("Jurassic Park", external_id=1)]
    # Its (deliberately misspelled) title makes the same query a literal
    # prefix match here, unlike the library's correctly-spelled title.
    title_index_rows = [{"id": 2, "t": "Jurasic Park Begins", "p": 10.0, "m": "movie"}]

    service = _build_service(tmp_path, library_rows=library, title_index_rows=title_index_rows)
    results = asyncio.run(service.combined_search("jurasic park"))

    assert results[0].in_library is False
    assert results[0].name == "Jurasic Park Begins"
