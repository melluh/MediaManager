"""
Resolving an importable directory to a single best match, and the
`.mediamanager` sidecar that caches that match inside the directory.
"""

import asyncio
import json
import os
import uuid
from pathlib import Path

import pytest

from media_manager.common.import_match import (
    ImportMatchConfidence,
    normalize_title,
)
from media_manager.common.import_sidecar import (
    SIDECAR_FILENAME,
    SIDECAR_VERSION,
    ImportMatchSidecar,
    delete_import_sidecar,
    read_import_sidecar,
    write_import_sidecar,
)
from media_manager.common.service import BaseMetadataService
from media_manager.config import get_config
from media_manager.metadataProvider.schemas import (
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.importer import MovieImportService
from media_manager.movies.schemas import Movie, MovieId


@pytest.fixture(autouse=True)
def _uncached_config():
    """
    The sidecar writer reads the cached config, which must not carry one
    test's settings into the next.
    """
    get_config.cache_clear()
    yield
    get_config.cache_clear()


class FakeMovieMetadataService:
    def __init__(self, results: list[MetaDataProviderSearchResult]) -> None:
        self.results = results
        self.calls: list[tuple[str, int]] = []

    async def search_for_movie(self, query, metadata_provider, max_pages=5):  # noqa: ARG002
        self.calls.append((query, max_pages))
        return list(self.results)


class FakeProvider:
    name = "tmdb"

    def __init__(self, movies_by_id: dict[int, Movie] | None = None) -> None:
        self.movies_by_id = movies_by_id or {}
        self.metadata_calls: list[int] = []

    async def get_movie_metadata(self, movie_id: int, language=None) -> Movie:  # noqa: ARG002
        self.metadata_calls.append(movie_id)
        if movie_id not in self.movies_by_id:
            msg = f"no such movie {movie_id}"
            raise KeyError(msg)
        return self.movies_by_id[movie_id]

    async def get_movie_images(self, movie_id: int):  # noqa: ARG002
        return [], []


def _result(name: str, year: int | None, external_id: int = 1):
    return MetaDataProviderSearchResult(
        overview=None,
        name=name,
        external_id=external_id,
        year=year,
        metadata_provider="tmdb",
        media_type=MediaType.movie,
        added=False,
    )


def _movie(name: str, year: int | None, external_id: int) -> Movie:
    return Movie(
        name=name,
        overview="",
        year=year,
        external_id=external_id,
        metadata_provider="tmdb",
    )


def _service(metadata_service: FakeMovieMetadataService) -> MovieImportService:
    return MovieImportService(
        movie_repository=None,
        torrent_service=None,
        notification_service=None,
        movie_metadata_service=metadata_service,
    )


def _resolve(directory: Path, results, movies_by_id=None):
    """Resolves one directory, returning the suggestion and the fakes used."""
    metadata_service = FakeMovieMetadataService(results)
    provider = FakeProvider(movies_by_id)
    suggestion = asyncio.run(
        _service(metadata_service).get_import_suggestion(
            movie_path=directory, metadata_provider=provider
        )
    )
    return suggestion, metadata_service, provider


def _directory(tmp_path: Path, name: str) -> Path:
    directory = tmp_path / name
    directory.mkdir()
    return directory


def test_normalize_title_ignores_case_accents_and_punctuation():
    assert normalize_title("Amélie") == normalize_title("AMELIE")
    assert normalize_title("Spider-Man: No Way Home") == "spider man no way home"
    assert normalize_title("WALL·E") == "wall e"
    assert normalize_title("  The   Matrix  ") == "the matrix"
    assert normalize_title("Mr. Robot") == normalize_title("mr robot")
    assert normalize_title("Fahrenheit 451") != normalize_title("Fahrenheit 452")


def test_a_matching_title_and_year_is_confident(tmp_path):
    directory = _directory(tmp_path, "Amelie (2001)")

    suggestion, _, _ = _resolve(
        directory, [_result("Amélie", 2001, external_id=194)]
    )

    assert suggestion.confidence is ImportMatchConfidence.confident
    assert suggestion.match.external_id == 194


def test_a_differing_year_is_only_a_best_guess(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")

    suggestion, _, _ = _resolve(
        directory, [_result("The Thing", 2011, external_id=2)]
    )

    assert suggestion.confidence is ImportMatchConfidence.best_guess
    assert suggestion.match.external_id == 2


def test_a_missing_year_is_only_a_best_guess(tmp_path):
    directory = _directory(tmp_path, "The Thing")

    suggestion, _, _ = _resolve(
        directory, [_result("The Thing", 1982, external_id=3)]
    )

    assert suggestion.confidence is ImportMatchConfidence.best_guess


def test_nothing_matching_leaves_no_preselected_match(tmp_path):
    directory = _directory(tmp_path, "some.scene.release.2019")

    suggestion, _, _ = _resolve(directory, [_result("Something Else", 2019)])

    assert suggestion.confidence is ImportMatchConfidence.none
    assert suggestion.match is None


def test_an_id_in_the_directory_name_is_resolved_without_searching(tmp_path):
    directory = _directory(tmp_path, "Dune (2021) [tmdbid-438631]")

    suggestion, metadata_service, provider = _resolve(
        directory, [], movies_by_id={438631: _movie("Dune", 2021, 438631)}
    )

    assert suggestion.confidence is ImportMatchConfidence.exact_id
    assert suggestion.match.external_id == 438631
    assert provider.metadata_calls == [438631]
    assert metadata_service.calls == []


def test_an_id_whose_title_disagrees_still_wins_at_a_lower_confidence(tmp_path):
    directory = _directory(tmp_path, "Dune Part Two (2024) [tmdbid-438631]")

    suggestion, metadata_service, _ = _resolve(
        directory, [], movies_by_id={438631: _movie("Dune", 2021, 438631)}
    )

    assert suggestion.confidence is ImportMatchConfidence.best_guess
    assert suggestion.match.external_id == 438631
    assert metadata_service.calls == []


def test_an_id_the_provider_cannot_resolve_falls_back_to_searching(tmp_path):
    directory = _directory(tmp_path, "Dune (2021) [tmdbid-999999]")

    suggestion, metadata_service, _ = _resolve(
        directory, [_result("Dune", 2021, external_id=438631)]
    )

    assert suggestion.confidence is ImportMatchConfidence.confident
    assert metadata_service.calls == [("Dune", 1)]


def test_an_id_for_another_provider_is_searched_instead(tmp_path):
    directory = _directory(tmp_path, "Dune (2021) [tvdbid-60625]")

    _, metadata_service, provider = _resolve(
        directory, [_result("Dune", 2021, external_id=438631)]
    )

    assert provider.metadata_calls == []
    assert metadata_service.calls == [("Dune", 1)]


def test_the_scan_only_ever_asks_for_one_page(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")

    _, metadata_service, _ = _resolve(directory, [])

    assert metadata_service.calls == [("The Thing", 1)]


def test_a_resolved_match_is_cached_in_the_directory(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")
    results = [_result("The Thing", 1982, external_id=1091)]

    first, _, _ = _resolve(directory, results)
    second, metadata_service, provider = _resolve(directory, results)

    assert (directory / SIDECAR_FILENAME).is_file()
    assert second.match.external_id == first.match.external_id
    assert second.confidence is first.confidence
    # Served from the sidecar: nothing was asked of the metadata provider.
    assert metadata_service.calls == []
    assert provider.metadata_calls == []


def test_a_negative_result_is_cached_too(tmp_path):
    directory = _directory(tmp_path, "unknown.release.group")

    _resolve(directory, [])
    suggestion, metadata_service, _ = _resolve(directory, [])

    assert suggestion.confidence is ImportMatchConfidence.none
    assert suggestion.match is None
    assert metadata_service.calls == []


def test_a_renamed_directory_is_resolved_again(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")
    write_import_sidecar(
        directory,
        ImportMatchSidecar(
            directory_name="Some Other Name (1982)",
            confidence=ImportMatchConfidence.confident,
            match=_result("Some Other Name", 1982, external_id=42),
        ),
    )

    suggestion, metadata_service, _ = _resolve(
        directory, [_result("The Thing", 1982, external_id=1091)]
    )

    assert metadata_service.calls == [("The Thing", 1)]
    assert suggestion.match.external_id == 1091


def test_deleting_a_sidecar_leaves_the_directory_uncached(tmp_path):
    # An imported directory is skipped by every later scan, so its cached
    # match is dead weight - and a stray file in the user's media directory.
    directory = _directory(tmp_path, "The Thing (1982)")
    write_import_sidecar(
        directory,
        ImportMatchSidecar(
            directory_name="The Thing (1982)",
            confidence=ImportMatchConfidence.confident,
            match=_result("The Thing", 1982, external_id=42),
        ),
    )
    assert (directory / SIDECAR_FILENAME).exists()

    delete_import_sidecar(directory)

    assert not (directory / SIDECAR_FILENAME).exists()
    # Deleting one that is already gone is not an error.
    delete_import_sidecar(directory)


def test_deleting_a_sidecar_in_a_read_only_directory_does_not_raise(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")
    write_import_sidecar(
        directory,
        ImportMatchSidecar(
            directory_name="The Thing (1982)",
            confidence=ImportMatchConfidence.confident,
            match=_result("The Thing", 1982, external_id=42),
        ),
    )
    directory.chmod(0o500)
    try:
        delete_import_sidecar(directory)
    finally:
        directory.chmod(0o700)


def test_a_malformed_sidecar_is_a_cache_miss(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")
    (directory / SIDECAR_FILENAME).write_text("{not json at all")

    assert read_import_sidecar(directory) is None

    suggestion, metadata_service, _ = _resolve(
        directory, [_result("The Thing", 1982, external_id=1091)]
    )

    assert metadata_service.calls == [("The Thing", 1)]
    assert suggestion.match.external_id == 1091


def test_an_unknown_sidecar_version_is_a_cache_miss(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")
    (directory / SIDECAR_FILENAME).write_text(
        json.dumps({"version": SIDECAR_VERSION + 1, "whatever": "comes next"})
    )

    assert read_import_sidecar(directory) is None

    _, metadata_service, _ = _resolve(
        directory, [_result("The Thing", 1982, external_id=1091)]
    )

    assert metadata_service.calls == [("The Thing", 1)]


@pytest.mark.skipif(
    os.geteuid() == 0, reason="root writes into read-only directories anyway"
)
def test_a_read_only_directory_does_not_break_the_scan(tmp_path):
    directory = _directory(tmp_path, "The Thing (1982)")
    directory.chmod(0o500)
    try:
        suggestion, _, _ = _resolve(
            directory, [_result("The Thing", 1982, external_id=1091)]
        )
    finally:
        directory.chmod(0o700)

    assert suggestion.confidence is ImportMatchConfidence.confident
    assert suggestion.match.external_id == 1091
    assert not (directory / SIDECAR_FILENAME).exists()


def test_sidecar_writing_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIAMANAGER_MISC__WRITE_IMPORT_SIDECARS", "false")
    get_config.cache_clear()
    directory = _directory(tmp_path, "The Thing (1982)")

    suggestion, _, _ = _resolve(
        directory, [_result("The Thing", 1982, external_id=1091)]
    )

    assert suggestion.match.external_id == 1091
    assert not (directory / SIDECAR_FILENAME).exists()


class FakeSearchRepository:
    """A library holding a few movies, queried both ways for comparison."""

    def __init__(self, stored: dict[int, tuple[MovieId, str]]) -> None:
        self.stored = stored
        self.queries = 0

    async def get_ids_by_external_ids(self, external_ids, metadata_provider):  # noqa: ARG002
        self.queries += 1
        wanted = set(external_ids)
        return {
            external_id: value
            for external_id, value in self.stored.items()
            if external_id in wanted
        }

    async def exists_by_external_id(self, external_id, metadata_provider):  # noqa: ARG002
        self.queries += 1
        return external_id in self.stored

    async def get_by_external_id(self, external_id, metadata_provider):  # noqa: ARG002
        self.queries += 1
        internal_id, slug = self.stored[external_id]
        return Movie(
            id=internal_id,
            slug=slug,
            name="stored",
            overview="",
            year=None,
            external_id=external_id,
            metadata_provider="tmdb",
        )


async def _added_by_the_old_loop(results, repository, provider_name):
    """The per-result lookup the bulk query replaced, kept as the reference."""
    for result in results:
        if await repository.exists_by_external_id(
            external_id=result.external_id, metadata_provider=provider_name
        ):
            result.added = True
            media = await repository.get_by_external_id(
                external_id=result.external_id, metadata_provider=provider_name
            )
            result.id = media.id
            result.slug = media.slug
    return results


def test_the_bulk_added_lookup_matches_the_old_per_result_loop():
    stored = {
        2: (MovieId(uuid.uuid4()), "the-thing-1982"),
        5: (MovieId(uuid.uuid4()), "dune-2021"),
    }
    searched = [_result(f"Movie {index}", 2000, index) for index in range(1, 7)]

    async def search(query, max_pages=5):  # noqa: ARG001
        return [result.model_copy(deep=True) for result in searched]

    provider = FakeProvider()
    bulk_repository = FakeSearchRepository(stored)
    bulk = asyncio.run(
        BaseMetadataService(repository=bulk_repository).search_for_media_base(
            query="anything", metadata_provider=provider, search_func=search
        )
    )

    loop_repository = FakeSearchRepository(stored)
    reference = asyncio.run(
        _added_by_the_old_loop(
            asyncio.run(search("anything")), loop_repository, provider.name
        )
    )

    assert [result.model_dump() for result in bulk] == [
        result.model_dump() for result in reference
    ]
    assert [result.added for result in bulk] == [False, True, False, False, True, False]
    # One query for the whole page, instead of one per result plus one more
    # per result already in the library.
    assert bulk_repository.queries == 1
    assert loop_repository.queries == len(searched) + len(stored)
