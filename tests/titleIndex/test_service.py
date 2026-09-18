import asyncio
import gzip
import json
from pathlib import Path

from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.service import TitleSuggestionService


class _StubRepository:
    def __init__(self, in_library_external_ids: set[int]) -> None:
        self._in_library_external_ids = in_library_external_ids

    async def get_ids_by_external_ids(
        self, external_ids: list[int], metadata_provider: str
    ) -> dict[int, tuple[str, str | None]]:
        assert metadata_provider == "tmdb"
        return {
            external_id: (f"internal-{external_id}", "some-slug")
            for external_id in external_ids
            if external_id in self._in_library_external_ids
        }


def _write_index(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")


def test_suggest_excludes_in_library_items_and_backfills_from_pool(
    tmp_path: Path,
) -> None:
    # "Backfill" here means TitleSuggestionService.suggest filters the *full*
    # ranked candidate list before slicing to max_results, rather than
    # slicing to max_results first and filtering after (which would leave
    # only 1 result once the top-ranked candidate is excluded). Confirmed by
    # deliberately simulating the buggy slice-then-filter order.
    rows = [
        {"id": 1, "t": "Space Adventure", "p": 90.0, "m": "movie"},
        {"id": 2, "t": "Space Adventure Two", "p": 80.0, "m": "movie"},
        {"id": 3, "t": "Space Adventure Three", "p": 70.0, "m": "movie"},
    ]
    _write_index(tmp_path / "title_index.ndjson.gz", rows)

    config = TitleIndexConfig(max_results=2)
    service = TitleSuggestionService(
        repositories={
            MediaType.movie: _StubRepository(in_library_external_ids={1}),
            MediaType.tv: _StubRepository(in_library_external_ids=set()),
        },
        directory=tmp_path,
        config=config,
    )

    suggestions = asyncio.run(service.suggest("Space Adventure"))

    ids = [suggestion.id for suggestion in suggestions]
    assert 1 not in ids
    assert len(suggestions) == 2
    assert set(ids) == {2, 3}


def test_suggest_returns_empty_when_index_missing(tmp_path: Path) -> None:
    service = TitleSuggestionService(
        repositories={
            MediaType.movie: _StubRepository(in_library_external_ids=set()),
            MediaType.tv: _StubRepository(in_library_external_ids=set()),
        },
        directory=tmp_path,
        config=TitleIndexConfig(),
    )

    suggestions = asyncio.run(service.suggest("anything"))

    assert suggestions == []
