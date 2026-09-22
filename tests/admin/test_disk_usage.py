import asyncio
from pathlib import Path

from media_manager.admin.service import AdminService


async def _gather_stats(*coros):
    return await asyncio.gather(*coros)


def test_stat_path_reports_usage_for_an_existing_directory(tmp_path):
    stat = asyncio.run(AdminService._stat_path("Movies", tmp_path))

    assert stat.device is not None
    assert stat.total_bytes is not None
    assert stat.total_bytes > 0


def test_stat_path_is_unavailable_for_a_missing_directory(tmp_path):
    stat = asyncio.run(AdminService._stat_path("Missing", tmp_path / "does-not-exist"))

    assert stat.device is None
    assert stat.total_bytes is None


def test_group_disk_usage_merges_names_sharing_a_filesystem(tmp_path):
    movies_dir = tmp_path / "movies"
    tv_dir = tmp_path / "tv"
    movies_dir.mkdir()
    tv_dir.mkdir()

    stats = asyncio.run(
        _gather_stats(
            AdminService._stat_path("Movies", movies_dir),
            AdminService._stat_path("TV Shows", tv_dir),
        )
    )

    result = AdminService._group_disk_usage(list(stats))

    assert len(result.entries) == 1
    entry = result.entries[0]
    assert entry.available
    assert set(entry.names) == {"Movies", "TV Shows"}
    assert set(entry.paths) == {str(movies_dir), str(tv_dir)}
    assert entry.total_bytes > 0


def test_group_disk_usage_keeps_unavailable_paths_separate_without_raising(tmp_path):
    available_dir = tmp_path / "movies"
    available_dir.mkdir()
    missing_path = tmp_path / "does-not-exist"

    stats = asyncio.run(
        _gather_stats(
            AdminService._stat_path("Movies", available_dir),
            AdminService._stat_path("Missing", missing_path),
        )
    )

    result = AdminService._group_disk_usage(list(stats))

    assert len(result.entries) == 2
    by_name = {entry.names[0]: entry for entry in result.entries}
    assert by_name["Movies"].available
    assert not by_name["Missing"].available
    assert by_name["Missing"].total_bytes == 0
    assert by_name["Missing"].paths == [str(missing_path)]


def test_get_disk_usage_enumerates_configured_paths(tmp_path):
    from media_manager.config import LibraryItem, MediaManagerConfig

    config = MediaManagerConfig()
    config.misc.movie_directory = tmp_path / "movies"
    config.misc.tv_directory = tmp_path / "tv"
    config.misc.torrent_directory = tmp_path / "torrents"
    config.misc.image_directory = tmp_path / "images"
    for directory in (
        config.misc.movie_directory,
        config.misc.tv_directory,
        config.misc.torrent_directory,
        config.misc.image_directory,
    ):
        Path(directory).mkdir()
    config.misc.movie_libraries = [
        LibraryItem(name="Anime Movies", path=str(config.misc.movie_directory))
    ]

    result = asyncio.run(AdminService.get_disk_usage(config))

    all_names = {name for entry in result.entries for name in entry.names}
    assert {"Movies", "TV Shows", "Torrents", "Images", "Anime Movies"} <= all_names
    # movie_directory and the "Anime Movies" library share one filesystem -
    # they should be merged into the same entry, not double-counted.
    movies_entry = next(e for e in result.entries if "Movies" in e.names)
    assert "Anime Movies" in movies_entry.names
