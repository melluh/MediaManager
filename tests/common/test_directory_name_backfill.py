import importlib.util
import sys
import types
from pathlib import Path

MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "b7e1c4d9a2f5_persist_media_directory_and_file_paths.py"
)


def _load_migration():
    # alembic/versions is not a package, so the module has to be loaded by path.
    spec = importlib.util.spec_from_file_location(
        "b7e1c4d9a2f5_persist_media_directory_and_file_paths", MIGRATION_PATH
    )
    module = importlib.util.module_from_spec(spec)
    # The repo's own `alembic/` directory shadows the installed package, so
    # `from alembic import op` cannot resolve here; the helper under test does not
    # touch `op`, so a stub is enough to get the module loaded.
    stub = types.ModuleType("alembic")
    stub.op = None
    saved = sys.modules.get("alembic")
    sys.modules["alembic"] = stub
    try:
        spec.loader.exec_module(module)
    finally:
        if saved is None:
            del sys.modules["alembic"]
        else:
            sys.modules["alembic"] = saved
    return module


migration = _load_migration()


def select(
    name="The Show",
    year=2020,
    provider="tmdb",
    external_id=123,
    entries=(),
    claimed=None,
):
    return migration.select_directory_name(
        name=name,
        year=year,
        provider=provider,
        external_id=external_id,
        entries=entries,
        claimed=set() if claimed is None else claimed,
    )


def test_canonical_name_wins_when_present():
    entries = [
        "The Show",
        "The Show (2020) [tmdbid-123]",
        "The Show (None) [tmdbid-123]",
    ]
    assert select(entries=entries) == "The Show (2020) [tmdbid-123]"


def test_none_year_variant_is_found_for_year_less_rows():
    entries = ["The Show (None) [tmdbid-123]", "The Show"]
    assert select(year=None, entries=entries) == "The Show (None) [tmdbid-123]"


def test_canonical_beats_none_variant_for_year_less_rows():
    entries = ["The Show (None) [tmdbid-123]", "The Show [tmdbid-123]"]
    assert select(year=None, entries=entries) == "The Show [tmdbid-123]"


def test_id_token_finds_retitled_directory():
    entries = ["Old Title (2020) [tmdbid-123]", "Unrelated (1999) [tmdbid-999]"]
    assert select(entries=entries) == "Old Title (2020) [tmdbid-123]"


def test_id_token_ignores_other_provider():
    entries = ["Old Title (2020) [tvdbid-123]"]
    assert select(entries=entries) == "The Show (2020) [tmdbid-123]"


def test_id_token_picks_lexicographically_first_match():
    entries = ["Zed [tmdb_123]", "Alpha [tmdb-123]", "Mid [tmdbid-123]"]
    assert select(entries=entries) == "Alpha [tmdb-123]"


def test_bare_name_is_only_a_last_resort():
    assert select(entries=["The Show"]) == "The Show"
    # An id-bearing directory exists too, so the bare name must not be chosen.
    assert (
        select(entries=["The Show", "Old Title [tmdbid-123]"])
        == "Old Title [tmdbid-123]"
    )


def test_claimed_directory_is_not_claimed_twice():
    entries = ["The Show"]
    claimed = {"The Show"}
    assert select(entries=entries, claimed=claimed) == "The Show (2020) [tmdbid-123]"


def test_claim_tracking_across_two_same_titled_rows():
    entries = ["The Show"]
    claimed = set()
    first = select(external_id=1, entries=entries, claimed=claimed)
    claimed.add(first)
    second = select(external_id=2, entries=entries, claimed=claimed)
    assert first == "The Show"
    assert second == "The Show (2020) [tmdbid-2]"


def test_nothing_on_disk_records_canonical_name():
    assert select(entries=[]) == "The Show (2020) [tmdbid-123]"
    assert select(year=None, entries=[]) == "The Show [tmdbid-123]"


def test_unreadable_parent_records_canonical_name():
    # entries is None when the parent directory could not be listed at all.
    assert select(entries=None) == "The Show (2020) [tmdbid-123]"


def test_name_is_sanitized():
    assert (
        select(name="The: Show/Two? ", entries=[]) == "The ShowTwo (2020) [tmdbid-123]"
    )
