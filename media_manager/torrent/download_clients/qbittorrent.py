import logging
import time
from typing import ClassVar

import qbittorrentapi
from qbittorrentapi import Conflict409Error

from media_manager.config import MediaManagerConfig
from media_manager.indexer.schemas import IndexerQueryResult
from media_manager.torrent.download_clients.abstract_download_client import (
    AbstractDownloadClient,
)
from media_manager.torrent.schemas import (
    DownloadProgress,
    DownloadState,
    Torrent,
    TorrentStatus,
)
from media_manager.torrent.utils import get_torrent_hash, sanitize_torrent_title

log = logging.getLogger(__name__)


class QbittorrentDownloadClient(AbstractDownloadClient):
    name = "qbittorrent"
    display_name = "qBittorrent"

    DOWNLOADING_STATE = (
        "allocating",
        "downloading",
        "metaDL",
        "pausedDL",
        "queuedDL",
        "stalledDL",
        "checkingDL",
        "forcedDL",
        "moving",
        "stoppedDL",
        "forcedMetaDL",
        "metaDL",
    )
    FINISHED_STATE = (
        "uploading",
        "pausedUP",
        "queuedUP",
        "stalledUP",
        "checkingUP",
        "forcedUP",
        "stoppedUP",
    )
    ERROR_STATE = ("missingFiles", "error", "checkingResumeData")
    UNKNOWN_STATE = ("unknown",)

    # Maps qBittorrent's raw `state` field to a client-neutral DownloadState.
    # See https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-4.1)
    # for the full list of states (both legacy "paused*" and current "stopped*"
    # names are handled since they vary by qBittorrent version).
    DOWNLOAD_STATE_MAP: ClassVar[dict[str, DownloadState]] = {
        "downloading": DownloadState.downloading,
        "forcedDL": DownloadState.downloading,
        "metaDL": DownloadState.downloading,
        "forcedMetaDL": DownloadState.downloading,
        "allocating": DownloadState.downloading,
        "moving": DownloadState.downloading,
        "queuedDL": DownloadState.queued,
        "queuedUP": DownloadState.queued,
        "stalledDL": DownloadState.stalled,
        "checkingDL": DownloadState.checking,
        "checkingUP": DownloadState.checking,
        "checkingResumeData": DownloadState.checking,
        "pausedDL": DownloadState.stopped,
        "stoppedDL": DownloadState.stopped,
        "uploading": DownloadState.seeding,
        "forcedUP": DownloadState.seeding,
        "stalledUP": DownloadState.seeding,
        "pausedUP": DownloadState.finished,
        "stoppedUP": DownloadState.finished,
        "missingFiles": DownloadState.error,
        "error": DownloadState.error,
        "unknown": DownloadState.unknown,
    }

    # How long to wait for an added torrent to show up in qBittorrent. Torrents added
    # by URL are fetched by qBittorrent in the background, so the add call itself can
    # report success (as "pending") for a torrent that never actually gets added.
    ADD_VERIFY_TIMEOUT_SECONDS = 30
    ADD_VERIFY_POLL_INTERVAL_SECONDS = 1

    def __init__(self) -> None:
        self.config = MediaManagerConfig().torrents.qbittorrent
        self.api_client = qbittorrentapi.Client(
            host=self.config.host,
            port=self.config.port,
            password=self.config.password,
            username=self.config.username,
            # When set, qbittorrent-api sends it as a bearer token on every request
            # instead of using a session cookie.
            api_key=self.config.api_key or None,
        )
        # Log in once; the session is shared by every thread using this client.
        # Don't log out after individual calls: that invalidates the session for
        # any other thread mid-request (which surfaces as 403 Forbidden errors).
        # qbittorrentapi re-authenticates on its own if the session expires.
        try:
            self.api_client.auth_log_in()
        except Exception:
            log.exception("Failed to log into qbittorrent")
            raise

        categories = self.api_client.torrents_categories()
        log.debug(f"Found following categories in qBittorrent: {categories}")
        if self.config.category_name in categories:
            category = categories.get(self.config.category_name)
            if category.get("savePath") == self.config.category_save_path:
                log.debug(
                    f"Category '{self.config.category_name}' already exists in qBittorrent with the correct save path."
                )
                return
            # category exists but with a different save path, attempt to update it
            log.debug(
                f"Category '{self.config.category_name}' already exists in qBittorrent but with a different save path. Attempting to update it."
            )
            try:
                self.api_client.torrents_edit_category(
                    name=self.config.category_name,
                    save_path=self.config.category_save_path,
                )
            except Conflict409Error:
                log.exception(
                    f"Attempt to update category '{self.config.category_name}' in qBittorrent with a different save"
                    f" path failed. The configured save path and the save path saved in Qbittorrent differ,"
                    f" manually update it in the qBittorrent WebUI or change the save path in the MediaManager"
                    f" config to match the one in qBittorrent."
                )
        else:
            # create category if it doesn't exist
            log.debug(
                f"Category '{self.config.category_name}' does not exist in qBittorrent. Attempting to create it."
            )
            try:
                self.api_client.torrents_create_category(
                    name=self.config.category_name,
                    save_path=self.config.category_save_path,
                )
            except Conflict409Error:
                log.exception(
                    f"Attempt to create category '{self.config.category_name}' in qBittorrent failed. The category already exists but was not found in the initial category list, manually check if the category exists in the qBittorrent WebUI or change the category name in the MediaManager config."
                )

    def download_torrent(self, indexer_result: IndexerQueryResult) -> Torrent:
        """
        Add a torrent to the download client and return the torrent object.

        :param indexer_result: The indexer query result of the torrent file to download.
        :return: The torrent object with calculated hash and initial status.
        """
        torrent_hash = get_torrent_hash(torrent=indexer_result)

        answer = self.api_client.torrents_add(
            category=self.config.category_name,
            urls=indexer_result.download_url,
            save_path=sanitize_torrent_title(indexer_result.title),
        )
        log.debug(f"qBittorrent torrents_add answer: {answer}")

        # Older qBittorrent versions answer "Ok."/"Fails.", newer ones return counts.
        if isinstance(answer, str):
            accepted = answer == "Ok."
        else:
            accepted = answer.get("failure_count", 0) == 0 and (
                answer.get("success_count", 0) + answer.get("pending_count", 0) > 0
            )
        if not accepted:
            msg = f"qBittorrent rejected torrent '{indexer_result.title}': {answer}"
            log.error(msg)
            raise RuntimeError(msg)

        self._wait_until_added(torrent_hash, indexer_result.title)
        log.info(f"Successfully added torrent to qBittorrent: {indexer_result.title}")

        # Create and return torrent object
        torrent = Torrent(
            status=TorrentStatus.unknown,
            title=indexer_result.title,
            hash=torrent_hash,
        )

        # Get initial status from download client
        torrent.status = self.get_torrent_status(torrent)

        return torrent

    def _wait_until_added(self, torrent_hash: str, title: str) -> None:
        """
        Block until qBittorrent lists the torrent, raising if it never shows up.

        :param torrent_hash: The info hash of the added torrent.
        :param title: The torrent title, for log and error messages.
        """
        deadline = time.monotonic() + self.ADD_VERIFY_TIMEOUT_SECONDS
        while True:
            if self.api_client.torrents_info(torrent_hashes=torrent_hash):
                return
            if time.monotonic() >= deadline:
                break
            time.sleep(self.ADD_VERIFY_POLL_INTERVAL_SECONDS)

        msg = (
            f"qBittorrent accepted torrent '{title}' but it did not appear within "
            f"{self.ADD_VERIFY_TIMEOUT_SECONDS}s. qBittorrent most likely failed to "
            f"fetch the download URL; check that it can reach the indexer and "
            f"check the qBittorrent log."
        )
        log.error(msg)
        raise RuntimeError(msg)

    def remove_torrent(self, torrent: Torrent, delete_data: bool = False) -> None:
        """
        Remove a torrent from the download client.

        :param torrent: The torrent to remove.
        :param delete_data: Whether to delete the downloaded data.
        """
        log.info(f"Removing torrent: {torrent.title}")
        self.api_client.torrents_delete(
            torrent_hashes=torrent.hash, delete_files=delete_data
        )

    def get_torrent_status(self, torrent: Torrent) -> TorrentStatus:
        """
        Get the status of a specific torrent.

        :param torrent: The torrent to get the status of.
        :return: The status of the torrent.
        """
        info = self.api_client.torrents_info(torrent_hashes=torrent.hash)

        if not info:
            log.warning(f"No information found for torrent: {torrent.id}")
            return TorrentStatus.unknown
        state: str = info[0]["state"]

        if state in self.DOWNLOADING_STATE:
            return TorrentStatus.downloading
        if state in self.FINISHED_STATE:
            return TorrentStatus.finished
        if state in self.ERROR_STATE:
            return TorrentStatus.error
        if state in self.UNKNOWN_STATE:
            return TorrentStatus.unknown
        return TorrentStatus.error

    def get_download_progress_bulk(
        self, torrents: list[Torrent]
    ) -> dict[str, DownloadProgress]:
        """
        Get live progress for the given torrents in a single request to qBittorrent,
        rather than one request per torrent.

        :param torrents: The torrents to look up.
        :return: A dict mapping torrent hash to its progress, for torrents qBittorrent
            currently knows about.
        """
        # Match case-insensitively: qBittorrent is expected to report lowercase
        # hex hashes, same as get_torrent_hash(), but nothing guarantees that
        # across versions, so don't rely on exact casing lining up.
        wanted_hashes = {torrent.hash.lower(): torrent.hash for torrent in torrents}
        info = self.api_client.torrents_info()

        progress: dict[str, DownloadProgress] = {}
        for t in info:
            original_hash = wanted_hashes.get(t["hash"].lower())
            if original_hash is None:
                continue
            eta = t.get("eta")
            progress[original_hash] = DownloadProgress(
                state=self.DOWNLOAD_STATE_MAP.get(t["state"], DownloadState.unknown),
                progress=round(t.get("progress", 0.0) * 100, 1),
                total_bytes=t.get("size"),
                downloaded_bytes=t.get("downloaded"),
                download_speed_bytes_per_second=t.get("dlspeed"),
                # qBittorrent reports 8640000 (100 days) as its "infinite/unknown" ETA sentinel.
                eta_seconds=eta if eta is not None and 0 <= eta < 8_640_000 else None,
                seeders=t.get("num_seeds"),
                leechers=t.get("num_leechs"),
            )
        return progress

    def pause_torrent(self, torrent: Torrent) -> None:
        """
        Pause a torrent download.

        :param torrent: The torrent to pause.
        """
        self.api_client.torrents_pause(torrent_hashes=torrent.hash)

    def resume_torrent(self, torrent: Torrent) -> None:
        """
        Resume a torrent download.

        :param torrent: The torrent to resume.
        """
        self.api_client.torrents_resume(torrent_hashes=torrent.hash)

    def ping(self) -> bool:
        # Call an endpoint that requires authentication. Merely logging in succeeds
        # whenever the credentials are valid, even if actual API calls are failing.
        try:
            self.api_client.app_version()
        except Exception:  # noqa: BLE001 # ping should report failure for any reason
            return False
        else:
            return True
