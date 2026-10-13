import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Literal, NamedTuple
from uuid import UUID

from media_manager.admin.schemas import (
    DiskUsageCategory,
    DiskUsageCategoryKey,
    DiskUsageEntry,
    DiskUsageStats,
    LargestMediaItem,
    LibraryStats,
)
from media_manager.config import LibraryItem, MediaManagerConfig
from media_manager.movies.repository import MovieRepository
from media_manager.tv.repository import TvRepository

log = logging.getLogger(__name__)


class _PathStat(NamedTuple):
    name: str
    path: Path
    device: int | None
    total_bytes: int | None
    used_bytes: int | None
    free_bytes: int | None


CategoryBytes = dict[int, dict[DiskUsageCategoryKey, int]]
"""Bytes per category, per filesystem (st_dev)."""

_CATEGORY_LABELS: dict[DiskUsageCategoryKey, str] = {
    "movies": "Movies",
    "tv": "TV Shows",
    "images": "Images",
}


_LARGEST_MEDIA_LIMIT = 20


class AdminService:
    def __init__(
        self, movie_repository: MovieRepository, tv_repository: TvRepository
    ) -> None:
        self.movie_repository = movie_repository
        self.tv_repository = tv_repository

    async def get_stats(self) -> LibraryStats:
        return LibraryStats(
            movie_count=await self.movie_repository.count_movies(),
            show_count=await self.tv_repository.count_shows(),
            episode_count=(
                await self.tv_repository.get_total_downloaded_episodes_count()
            ),
        )

    async def get_disk_usage(self, config: MediaManagerConfig) -> DiskUsageStats:
        """
        Reports disk usage for every configured media/torrent path, grouped
        by filesystem (st_dev) so that libraries sharing one mount are
        reported once instead of being double-counted. A path that can't be
        statted (missing/unmounted) gets its own entry with available=False
        rather than failing the whole request.

        Each filesystem's used space is broken down into categories. Movies
        and TV shows are summed from the file sizes stored by the periodic
        probe refresh, attributed to the filesystem of their library's root.
        Images have no stored sizes, so the image directory is walked. The
        rest is "other": torrents count there only when they were never
        imported, since an imported torrent is hardlinked into the library
        and already counted as a movie or episode.
        """
        misc = config.misc
        candidates: list[tuple[str, Path]] = [
            ("Movies", misc.movie_directory),
            ("TV Shows", misc.tv_directory),
            ("Torrents", misc.torrent_directory),
            ("Images", misc.image_directory),
            *((library.name, Path(library.path)) for library in misc.movie_libraries),
            *((library.name, Path(library.path)) for library in misc.tv_libraries),
        ]

        stats = await asyncio.gather(
            *(AdminService._stat_path(name, path) for name, path in candidates)
        )
        device_by_path = {stat.path: stat.device for stat in stats}

        category_bytes: CategoryBytes = {}

        def add(path: Path, key: DiskUsageCategoryKey, size: int) -> None:
            device = device_by_path.get(path)
            if device is None:
                return
            per_device = category_bytes.setdefault(device, {})
            per_device[key] = per_device.get(key, 0) + size

        movie_sizes = await self.movie_repository.sum_file_sizes_by_library()
        for library, size in movie_sizes.items():
            root = AdminService._library_root(
                library, misc.movie_directory, misc.movie_libraries
            )
            add(root, "movies", size)
        tv_sizes = await self.tv_repository.sum_file_sizes_by_library()
        for library, size in tv_sizes.items():
            root = AdminService._library_root(
                library, misc.tv_directory, misc.tv_libraries
            )
            add(root, "tv", size)
        if device_by_path.get(misc.image_directory) is not None:
            image_bytes = await asyncio.to_thread(
                AdminService._directory_size, misc.image_directory
            )
            add(misc.image_directory, "images", image_bytes)

        result = AdminService._group_disk_usage(stats, category_bytes)
        result.largest_media = await self._largest_media()
        return result

    async def _largest_media(self) -> list[LargestMediaItem]:
        """The movies and the shows taking up the most space, up to
        `_LARGEST_MEDIA_LIMIT` of each, mixed and largest first. Both are
        kept in full so the page can show the top movies, top shows, or the
        top of both combined."""
        movies = await self.movie_repository.largest_movies(_LARGEST_MEDIA_LIMIT)
        shows = await self.tv_repository.largest_shows(_LARGEST_MEDIA_LIMIT)
        items = [
            *(AdminService._largest_item("movie", row) for row in movies),
            *(AdminService._largest_item("show", row) for row in shows),
        ]
        items.sort(key=lambda item: item.bytes, reverse=True)
        return items

    @staticmethod
    def _largest_item(
        media_type: Literal["movie", "show"],
        row: tuple[UUID, str, str, int | None, int],
    ) -> LargestMediaItem:
        media_id, slug, name, year, size = row
        return LargestMediaItem(
            id=media_id,
            slug=slug,
            name=name,
            year=year,
            media_type=media_type,
            bytes=size,
        )

    @staticmethod
    def _library_root(
        library: str, default_dir: Path, libraries: list[LibraryItem]
    ) -> Path:
        """The directory a library's media live in, resolved the same way as
        `get_root_directory` does for a single media item."""
        for item in libraries:
            if item.name == library:
                return Path(item.path)
        return default_dir

    @staticmethod
    def _directory_size(root: Path) -> int:
        """
        Bytes allocated to every file under `root`, like `du -sx`: symlinks
        aren't followed, other filesystems mounted inside aren't entered, and
        a hardlinked file is counted once.
        """
        try:
            root_device = root.stat().st_dev
        except OSError:
            return 0
        seen: set[int] = set()
        total = 0
        pending = [root]
        while pending:
            directory = pending.pop()
            try:
                with os.scandir(directory) as scan:
                    entries = list(scan)
            except OSError:
                continue
            for entry in entries:
                try:
                    stat = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.st_dev != root_device:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False) and stat.st_ino not in seen:
                    seen.add(stat.st_ino)
                    total += stat.st_blocks * 512
        return total

    @staticmethod
    async def _stat_path(name: str, path: Path) -> _PathStat:
        try:
            usage = await asyncio.to_thread(shutil.disk_usage, path)
            device = (await asyncio.to_thread(os.stat, path)).st_dev
        except OSError:
            log.warning("Could not stat path %s (%s) for disk usage", name, path)
            return _PathStat(name, path, None, None, None, None)
        else:
            return _PathStat(name, path, device, usage.total, usage.used, usage.free)

    @staticmethod
    def _group_disk_usage(
        stats: list[_PathStat], category_bytes: CategoryBytes
    ) -> DiskUsageStats:
        groups: dict[int, DiskUsageEntry] = {}
        unavailable: list[DiskUsageEntry] = []

        for stat in stats:
            if stat.device is None:
                unavailable.append(
                    DiskUsageEntry(
                        names=[stat.name],
                        paths=[str(stat.path)],
                        total_bytes=0,
                        used_bytes=0,
                        free_bytes=0,
                        available=False,
                    )
                )
                continue

            existing = groups.get(stat.device)
            if existing is None:
                groups[stat.device] = DiskUsageEntry(
                    names=[stat.name],
                    paths=[str(stat.path)],
                    total_bytes=stat.total_bytes or 0,
                    used_bytes=stat.used_bytes or 0,
                    free_bytes=stat.free_bytes or 0,
                )
            else:
                existing.names.append(stat.name)
                existing.paths.append(str(stat.path))

        for device, entry in groups.items():
            entry.categories = AdminService._categories(
                entry.used_bytes, category_bytes.get(device, {})
            )

        return DiskUsageStats(entries=[*groups.values(), *unavailable])

    @staticmethod
    def _categories(
        used_bytes: int, sizes: dict[DiskUsageCategoryKey, int]
    ) -> list[DiskUsageCategory]:
        categories = [
            DiskUsageCategory(key=key, label=label, bytes=sizes[key])
            for key, label in _CATEGORY_LABELS.items()
            if sizes.get(key)
        ]
        other = max(0, used_bytes - sum(category.bytes for category in categories))
        return [*categories, DiskUsageCategory(key="other", label="Other", bytes=other)]
