import asyncio
from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID, uuid4

from media_manager.common.schemas import BaseMedia
from media_manager.search.config import SearchConfig
from media_manager.search.schemas import MediaType
from media_manager.search.service import SearchService
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.service import TitleSuggestionService


@dataclass(slots=True)
class _NameRow:
    id: UUID
    name: str
    slug: str | None


class _StubRepository:
    """Minimal stand-in for `BaseRepository`, exposing only what `SearchService` needs."""

    def __init__(self, rows: list[BaseMedia]) -> None:
        self._rows = {row.id: row for row in rows}

    async def get_all_names(self) -> list[_NameRow]:
        return [_NameRow(id=row.id, name=row.name, slug=row.slug) for row in self._rows.values()]

    async def get_by_ids_for_search(self, ids: Collection[UUID]) -> list[BaseMedia]:
        return [self._rows[i] for i in ids if i in self._rows]

    async def get_ids_by_external_ids(
        self, external_ids: Collection[int], metadata_provider: str
    ) -> dict[int, tuple[UUID, str | None]]:
        assert metadata_provider == "tmdb"
        assert external_ids is not None
        return {}


def _media(name: str, external_id: int) -> BaseMedia:
    return BaseMedia(
        id=uuid4(),
        name=name,
        slug=name.lower().replace(" ", "-"),
        overview="",
        year=2001,
        external_id=external_id,
        metadata_provider="tmdb",
    )


def _empty_title_suggestion_service(tmp_path) -> TitleSuggestionService:
    # No title-index file at tmp_path -> title_index.suggest_scored returns
    # [] gracefully, isolating these tests to the library-search path alone.
    return TitleSuggestionService(
        repositories={},
        directory=tmp_path,
        config=TitleIndexConfig(),
    )


def test_search_finds_library_item_by_acronym(tmp_path) -> None:
    # The user's core ask: once "The Lord of the Rings" is added to the
    # library, typing "lotr" must still find it - not just typo tolerance,
    # abbreviation tolerance too.
    lotr = _media("The Lord of the Rings", external_id=1)
    other = _media("Inception", external_id=2)

    service = SearchService(
        repositories={
            MediaType.movie: _StubRepository([lotr, other]),
            MediaType.tv: _StubRepository([]),
        },
        title_suggestion_service=_empty_title_suggestion_service(tmp_path),
        config=SearchConfig(),
    )

    results = asyncio.run(service.search("lotr"))

    assert [r.name for r in results] == ["The Lord of the Rings"]


def test_search_finds_library_item_by_typo(tmp_path) -> None:
    jurassic = _media("Jurassic Park", external_id=1)

    service = SearchService(
        repositories={
            MediaType.movie: _StubRepository([jurassic]),
            MediaType.tv: _StubRepository([]),
        },
        title_suggestion_service=_empty_title_suggestion_service(tmp_path),
        config=SearchConfig(),
    )

    results = asyncio.run(service.search("Jurasic Park"))

    assert [r.name for r in results] == ["Jurassic Park"]


def test_search_ranks_across_media_types_together_not_a_fixed_per_type_quota(
    tmp_path,
) -> None:
    # A movie exact match must not be crowded out by unrelated, lower-quality
    # matches from the other media type filling a fixed per-type quota - both
    # pools are ranked together now.
    movie = _media("Firefly", external_id=1)
    show = _media("Firefly", external_id=2)

    service = SearchService(
        repositories={
            MediaType.movie: _StubRepository([movie]),
            MediaType.tv: _StubRepository([show]),
        },
        title_suggestion_service=_empty_title_suggestion_service(tmp_path),
        config=SearchConfig(max_results=1),
    )

    results = asyncio.run(service.search("Firefly"))

    # Both are equally-good exact structural matches with the same bonus;
    # either could legitimately win the single slot, but exactly one must.
    assert len(results) == 1
    assert results[0].name == "Firefly"
