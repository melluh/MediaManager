import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import NamedTuple

from media_manager.admin.schemas import DiskUsageEntry, DiskUsageStats, LibraryStats
from media_manager.config import MediaManagerConfig
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
            episode_count=await self.tv_repository.count_episodes(),
        )

    @staticmethod
    async def get_disk_usage(config: MediaManagerConfig) -> DiskUsageStats:
        """
        Reports disk usage for every configured media/torrent path, grouped
        by filesystem (st_dev) so that libraries sharing one mount are
        reported once instead of being double-counted. A path that can't be
        statted (missing/unmounted) gets its own entry with available=False
        rather than failing the whole request.
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
        return AdminService._group_disk_usage(stats)

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
    def _group_disk_usage(stats: list[_PathStat]) -> DiskUsageStats:
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

        return DiskUsageStats(entries=[*groups.values(), *unavailable])
