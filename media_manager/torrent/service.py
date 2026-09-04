import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import media_manager.metadataProvider.utils
from media_manager.exceptions import InvalidConfigError
from media_manager.indexer.schemas import IndexerQueryResult
from media_manager.movies.schemas import Movie, MovieFile
from media_manager.torrent.manager import DownloadManager, get_download_manager
from media_manager.torrent.repository import TorrentRepository
from media_manager.torrent.schemas import (
    DownloadProgress,
    Torrent,
    TorrentId,
    TorrentImportCandidate,
    TorrentMedia,
    TorrentStatus,
    TorrentWithProgress,
    download_state_to_torrent_status,
)
from media_manager.torrent.utils import get_torrent_filepath, list_torrent_media_files
from media_manager.torrent.video_probe import probe_video_files, resolve_file_quality
from media_manager.tv.schemas import EpisodeFile, Show, ShowSummary

log = logging.getLogger(__name__)


class TorrentService:
    def __init__(
        self,
        torrent_repository: TorrentRepository,
        download_manager: DownloadManager | None = None,
    ) -> None:
        self.torrent_repository = torrent_repository
        self.download_manager = download_manager or get_download_manager()

    async def get_episode_files_of_torrent(
        self, torrent: Torrent
    ) -> list[EpisodeFile]:
        """
        Returns all episode files of a torrent
        :param torrent: the torrent to get the episode files of
        :return: list of episode files
        """
        return await self.torrent_repository.get_episode_files_of_torrent(
            torrent_id=torrent.id
        )

    async def get_show_of_torrent(self, torrent: Torrent) -> Show | None:
        """
        Returns the show of a torrent
        :param torrent: the torrent to get the show of
        :return: the show of the torrent
        """
        return await self.torrent_repository.get_show_of_torrent(torrent_id=torrent.id)

    async def get_movie_of_torrent(self, torrent: Torrent) -> Movie | None:
        """
        Returns the movie of a torrent
        :param torrent: the torrent to get the movie of
        :return: the movie of the torrent
        """
        return await self.torrent_repository.get_movie_of_torrent(torrent_id=torrent.id)

    async def download(
        self, indexer_result: IndexerQueryResult, user_id: UUID | None = None
    ) -> Torrent:
        log.info(f"Starting download for torrent: {indexer_result.title}")
        torrent = await asyncio.to_thread(self.download_manager.download, indexer_result)

        if user_id is not None:
            torrent.initiated_by_user_id = user_id
            torrent.initiated_at = datetime.now(UTC)

        torrent.indexer = indexer_result.indexer
        torrent.comments = indexer_result.comments

        return await self.torrent_repository.save_torrent(torrent=torrent)

    async def get_torrent_status(self, torrent: Torrent) -> Torrent:
        torrent.status = await asyncio.to_thread(
            self.download_manager.get_torrent_status, torrent
        )
        await self.torrent_repository.save_torrent(torrent=torrent)
        return torrent

    async def cancel_download(
        self, torrent: Torrent, delete_files: bool = False
    ) -> Torrent:
        """
        cancels download of a torrent

        :param delete_files: Deletes the downloaded files of the torrent too, deactivated by default
        :param torrent: the torrent to cancel
        """
        log.info(f"Cancelling download for torrent: {torrent.title}")
        await asyncio.to_thread(
            self.download_manager.remove_torrent, torrent, delete_data=delete_files
        )
        return await self.get_torrent_status(torrent=torrent)

    async def cancel_torrent(
        self, torrent: Torrent, remove_from_client: bool = False
    ) -> Torrent:
        """
        Marks a torrent as cancelled so it stops showing up on the user's
        homepage, without deleting it (or its associated media files) from
        the database.

        :param remove_from_client: Also removes the torrent from the download
            client, without deleting its downloaded data. Best-effort: a
            client-side failure to remove it doesn't stop the torrent from
            being marked cancelled.
        """
        log.info(f"Cancelling torrent: {torrent.title}")
        if remove_from_client:
            try:
                await asyncio.to_thread(
                    self.download_manager.remove_torrent, torrent, delete_data=False
                )
            except (RuntimeError, InvalidConfigError):
                log.exception(
                    f"Failed to remove torrent from download client: {torrent.title}"
                )
        torrent.cancelled = True
        return await self.torrent_repository.save_torrent(torrent=torrent)

    async def pause_download(self, torrent: Torrent) -> Torrent:
        """
        pauses download of a torrent

        :param torrent: the torrent to pause
        """
        log.info(f"Pausing download for torrent: {torrent.title}")
        await asyncio.to_thread(self.download_manager.pause_torrent, torrent)
        return await self.get_torrent_status(torrent=torrent)

    async def resume_download(self, torrent: Torrent) -> Torrent:
        """
        resumes download of a torrent

        :param torrent: the torrent to resume
        """
        log.info(f"Resuming download for torrent: {torrent.title}")
        await asyncio.to_thread(self.download_manager.resume_torrent, torrent)
        return await self.get_torrent_status(torrent=torrent)

    async def get_all_torrents(self) -> list[Torrent]:
        all_torrents = await self.torrent_repository.get_all_torrents()
        torrents: list[Torrent] = []
        for t in all_torrents:
            try:
                torrents.append(await self.get_torrent_status(t))
            except Exception:
                log.exception(f"Error fetching status for torrent {t.title}")
        return torrents

    async def get_completed_torrents(self) -> list[Torrent]:
        return [
            t
            for t in await self.get_all_torrents()
            if t.status == TorrentStatus.finished and not t.imported
        ]

    async def get_torrent_by_id(self, torrent_id: TorrentId) -> Torrent:
        return await self.get_torrent_status(
            await self.torrent_repository.get_torrent_by_id(torrent_id=torrent_id)
        )

    async def delete_torrent(self, torrent_id: TorrentId) -> None:
        log.info(f"Deleting torrent with ID: {torrent_id}")
        t = await self.torrent_repository.get_torrent_by_id(torrent_id=torrent_id)
        delete_media_files = not t.imported
        await self.torrent_repository.delete_torrent(
            torrent_id=torrent_id, delete_associated_media_files=delete_media_files
        )

    async def get_movie_files_of_torrent(self, torrent: Torrent) -> list[MovieFile]:
        return await self.torrent_repository.get_movie_files_of_torrent(
            torrent_id=torrent.id
        )

    async def get_import_candidates(
        self, torrent: Torrent
    ) -> list[TorrentImportCandidate]:
        """
        Lists the video files found in a torrent's download directory, with
        enough detail (size, quality, duration) for a user to pick which one
        should actually be imported.
        """
        video_files, sizes_by_file = await asyncio.to_thread(
            self._list_video_files_with_sizes, torrent
        )
        probes = await probe_video_files(video_files)

        torrent_dir = get_torrent_filepath(torrent=torrent)
        candidates = []
        for file, probe in zip(video_files, probes, strict=True):
            candidates.append(
                TorrentImportCandidate(
                    relative_path=file.relative_to(torrent_dir).as_posix(),
                    file_name=file.name,
                    size_bytes=sizes_by_file[file],
                    quality=resolve_file_quality(
                        probe.quality, file.name, torrent.quality
                    ),
                    duration_seconds=probe.duration_seconds,
                )
            )
        return candidates

    @staticmethod
    def _list_video_files_with_sizes(
        torrent: Torrent,
    ) -> tuple[list[Path], dict[Path, int]]:
        video_files, _ = list_torrent_media_files(torrent=torrent)
        return video_files, {file: file.stat().st_size for file in video_files}

    async def get_own_torrents(self, user_id: UUID) -> list[TorrentWithProgress]:
        """
        Returns the torrents initiated by a user that are still downloading
        (i.e. not yet imported), with their current download status and, if the
        download client supports it, live progress.
        """
        own = await self.torrent_repository.get_active_torrents_initiated_by_user(
            user_id=user_id
        )
        torrents, progress_by_hash = await self._resolve_progress_and_status(own)
        media_by_torrent_id = await self._resolve_media(torrents)
        numbers_by_torrent_id = await self._resolve_season_and_episode_numbers(torrents)

        result = []
        for t in torrents:
            seasons, episodes = numbers_by_torrent_id.get(t.id, ([], []))
            result.append(
                TorrentWithProgress(
                    **t.model_dump(),
                    download_progress=progress_by_hash.get(t.hash),
                    media=media_by_torrent_id.get(t.id),
                    seasons=seasons,
                    # Episode numbers only mean something within a single season.
                    episodes=episodes if len(seasons) == 1 else [],
                )
            )
        return result

    async def _resolve_season_and_episode_numbers(
        self, torrents: list[Torrent]
    ) -> dict[TorrentId, tuple[list[int], list[int]]]:
        """
        Bulk-resolves the season and episode numbers each of the given torrents
        covers, keyed by torrent id. Movie torrents are absent from the result.
        """
        try:
            repository = self.torrent_repository
            return await repository.get_season_and_episode_numbers_of_torrents(
                torrent_ids=[t.id for t in torrents]
            )
        except Exception:
            log.exception("Error resolving seasons/episodes for own torrents")
            return {}

    async def _resolve_progress_and_status(
        self, torrents: list[Torrent]
    ) -> tuple[list[Torrent], dict[str, DownloadProgress]]:
        """
        Bulk-fetches live download progress for the given torrents and, for any
        the client reported on, reconciles their persisted TorrentStatus with the
        state that implies (writing to the DB only when it actually changed).

        Torrents the bulk fetch has no progress for (client doesn't support it,
        or is unavailable) fall back to the older per-torrent status check.
        """
        progress_by_hash: dict[str, DownloadProgress] = {}
        try:
            progress_by_hash = await asyncio.to_thread(
                self.download_manager.get_download_progress_bulk, torrents
            )
        except Exception:
            log.exception("Error fetching download progress")

        resolved: list[Torrent] = []
        for t in torrents:
            progress = progress_by_hash.get(t.hash)
            if progress is None:
                try:
                    resolved.append(await self.get_torrent_status(t))
                except Exception:
                    log.exception(f"Error fetching status for torrent {t.title}")
                    resolved.append(t)
                continue

            derived_status = download_state_to_torrent_status(progress.state)
            if derived_status != t.status:
                t.status = derived_status
                try:
                    await self.torrent_repository.save_torrent(torrent=t)
                except Exception:
                    log.exception(f"Error saving status for torrent {t.title}")
            resolved.append(t)

        return resolved, progress_by_hash

    async def _resolve_media(
        self, torrents: list[Torrent]
    ) -> dict[TorrentId, TorrentMedia]:
        """
        Bulk-resolves the movie/show each of the given torrents belongs to (if
        any), including poster/backdrop images, keyed by torrent id.
        """
        media_by_torrent_id: dict[TorrentId, TorrentMedia] = {}
        try:
            torrent_ids = [t.id for t in torrents]
            # Sequential, not gathered: both calls share self.db, and AsyncSession
            # doesn't support concurrent use from multiple tasks.
            movies_by_torrent_id = await self.torrent_repository.get_movies_of_torrents(
                torrent_ids=torrent_ids
            )
            shows_by_torrent_id = await self.torrent_repository.get_shows_of_torrents(
                torrent_ids=torrent_ids
            )
            # `images` isn't a DB column - it's resolved from disk, batched
            # across every movie/show in play here in one call.
            media_ids = [m.id for m in movies_by_torrent_id.values()] + [
                s.id for s in shows_by_torrent_id.values()
            ]
            images_by_media_id = await asyncio.to_thread(
                media_manager.metadataProvider.utils.get_available_media_images_many,
                media_ids,
            )
            for torrent_id, movie in movies_by_torrent_id.items():
                media_by_torrent_id[torrent_id] = self._build_torrent_media(
                    movie, is_show=False, images_by_media_id=images_by_media_id
                )
            for torrent_id, show in shows_by_torrent_id.items():
                media_by_torrent_id[torrent_id] = self._build_torrent_media(
                    show, is_show=True, images_by_media_id=images_by_media_id
                )
        except Exception:
            log.exception("Error resolving media for own torrents")

        return media_by_torrent_id

    @staticmethod
    def _build_torrent_media(
        media: Movie | ShowSummary,
        *,
        is_show: bool,
        images_by_media_id: dict[str, dict[str, str]],
    ) -> TorrentMedia:
        return TorrentMedia(
            id=media.id,
            name=media.name,
            slug=media.slug,
            year=media.year,
            is_show=is_show,
            metadata_updated_at=media.metadata_updated_at,
            images=images_by_media_id.get(str(media.id), {}),
        )
