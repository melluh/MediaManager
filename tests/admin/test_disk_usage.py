import asyncio
from pathlib import Path

from media_manager.admin.service import AdminService, _PathStat


async def _gather_stats(*coros):
    return await asyncio.gather(*coros)


class _StubRepository:
    def __init__(self, sizes: dict[str, int] | None = None) -> None:
        self.sizes = sizes or {}

    async def sum_file_sizes_by_library(self) -> dict[str, int]:
        return self.sizes


def _admin_service(
    movie_sizes: dict[str, int] | None = None,
    tv_sizes: dict[str, int] | None = None,
) -> AdminService:
    return AdminService(
        movie_repository=_StubRepository(movie_sizes),  # type: ignore[arg-type]
        tv_repository=_StubRepository(tv_sizes),  # type: ignore[arg-type]
    )


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

    result = AdminService._group_disk_usage(list(stats), {})

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

    result = AdminService._group_disk_usage(list(stats), {})

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

    result = asyncio.run(_admin_service().get_disk_usage(config))

    all_names = {name for entry in result.entries for name in entry.names}
    assert {"Movies", "TV Shows", "Torrents", "Images", "Anime Movies"} <= all_names
    # movie_directory and the "Anime Movies" library share one filesystem -
    # they should be merged into the same entry, not double-counted.
    movies_entry = next(e for e in result.entries if "Movies" in e.names)
    assert "Anime Movies" in movies_entry.names


def test_group_disk_usage_breaks_used_space_into_categories():
    stats = [
        _PathStat("Movies", Path("/movies"), 1, 1000, 600, 400),
        _PathStat("Images", Path("/images"), 1, 1000, 600, 400),
        _PathStat("Torrents", Path("/torrents"), 2, 500, 50, 450),
        _PathStat("Missing", Path("/missing"), None, None, None, None),
    ]

    result = AdminService._group_disk_usage(
        stats, {1: {"movies": 400, "images": 50, "tv": 0}}
    )

    by_name = {entry.names[0]: entry for entry in result.entries}
    assert [(c.key, c.bytes) for c in by_name["Movies"].categories] == [
        ("movies", 400),
        ("images", 50),
        ("other", 150),
    ]
    assert [(c.key, c.bytes) for c in by_name["Torrents"].categories] == [
        ("other", 50)
    ]
    assert by_name["Missing"].categories == []


def test_group_disk_usage_never_reports_negative_other():
    stats = [_PathStat("Movies", Path("/movies"), 1, 1000, 100, 900)]

    result = AdminService._group_disk_usage(stats, {1: {"movies": 150}})

    other = result.entries[0].categories[-1]
    assert other.key == "other"
    assert other.bytes == 0


def test_directory_size_counts_hardlinks_once_and_skips_symlinks(tmp_path):
    root = tmp_path / "images"
    (root / "nested").mkdir(parents=True)
    image = root / "nested" / "poster.jpg"
    image.write_bytes(b"x" * 10_000)
    (root / "hardlink.jpg").hardlink_to(image)
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"y" * 100_000)
    (root / "link.bin").symlink_to(outside)

    size = AdminService._directory_size(root)

    assert size == image.stat().st_blocks * 512


def test_get_disk_usage_attributes_library_sizes_to_their_filesystem(tmp_path):
    from media_manager.config import LibraryItem, MediaManagerConfig

    config = MediaManagerConfig()
    config.misc.movie_directory = tmp_path / "movies"
    config.misc.tv_directory = tmp_path / "tv"
    config.misc.torrent_directory = tmp_path / "torrents"
    config.misc.image_directory = tmp_path / "images"
    anime = tmp_path / "anime"
    for directory in (
        config.misc.movie_directory,
        config.misc.tv_directory,
        config.misc.torrent_directory,
        config.misc.image_directory,
        anime,
    ):
        Path(directory).mkdir()
    (Path(config.misc.image_directory) / "poster.jpg").write_bytes(b"x" * 10_000)
    config.misc.tv_libraries = [LibraryItem(name="Anime", path=str(anime))]
    service = _admin_service(
        movie_sizes={"Default": 1_000},
        tv_sizes={"Default": 200, "Anime": 30, "Removed Library": 4},
    )

    result = asyncio.run(service.get_disk_usage(config))

    # Everything lives on tmp_path's filesystem, so there is one entry.
    assert len(result.entries) == 1
    sizes = {c.key: c.bytes for c in result.entries[0].categories}
    assert sizes["movies"] == 1_000
    # A library no longer in the config falls back to the default directory,
    # just as its media's files are resolved.
    assert sizes["tv"] == 234
    assert sizes["images"] > 0
    assert "other" in sizes
