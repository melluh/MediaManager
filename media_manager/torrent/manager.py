import asyncio
import logging
import threading
from datetime import datetime, timezone

from media_manager.config import MediaManagerConfig
from media_manager.indexer.schemas import IndexerQueryResult
from media_manager.torrent.download_clients.abstract_download_client import (
    AbstractDownloadClient,
)
from media_manager.torrent.download_clients.qbittorrent import QbittorrentDownloadClient
from media_manager.torrent.download_clients.sabnzbd import SabnzbdDownloadClient
from media_manager.torrent.download_clients.transmission import (
    TransmissionDownloadClient,
)
from media_manager.torrent.schemas import Torrent, TorrentStatus

log = logging.getLogger(__name__)

_RECONNECT_INTERVAL = 60  # seconds between reconnection attempts for a failed client


class DownloadManager:
    """
    Manages download clients and routes downloads to the appropriate client.
    Designed as a long-lived singleton; obtain via get_download_manager().
    """

    def __init__(self) -> None:
        self._torrent_client: AbstractDownloadClient | None = None
        self._usenet_client: AbstractDownloadClient | None = None
        self._torrent_error: str | None = None
        self._usenet_error: str | None = None
        self._torrent_last_attempt: datetime | None = None
        self._usenet_last_attempt: datetime | None = None
        self.config = MediaManagerConfig().torrents
        self._lock = threading.Lock()
        self._initialize_clients()

    # ------------------------------------------------------------------
    # Initialization & reconnection (synchronous, safe for thread pool)
    # ------------------------------------------------------------------

    def _try_init_torrent(self) -> None:
        """Try to initialize the torrent client. Updates internal state."""
        self._torrent_last_attempt = datetime.now(timezone.utc)

        if self.config.qbittorrent.enabled:
            try:
                self._torrent_client = QbittorrentDownloadClient()
                self._torrent_error = None
                log.info("qBittorrent client connected")
                return
            except Exception as e:
                self._torrent_client = None
                self._torrent_error = str(e)
                log.warning("Failed to initialize qBittorrent: %s", e)

        if self.config.transmission.enabled:
            try:
                self._torrent_client = TransmissionDownloadClient()
                self._torrent_error = None
                log.info("Transmission client connected")
            except Exception as e:
                self._torrent_client = None
                self._torrent_error = str(e)
                log.warning("Failed to initialize Transmission: %s", e)

    def _try_init_usenet(self) -> None:
        """Try to initialize the usenet client. Updates internal state."""
        self._usenet_last_attempt = datetime.now(timezone.utc)

        if self.config.sabnzbd.enabled:
            try:
                self._usenet_client = SabnzbdDownloadClient()
                self._usenet_error = None
                log.info("SABnzbd client connected")
            except Exception as e:
                self._usenet_client = None
                self._usenet_error = str(e)
                log.warning("Failed to initialize SABnzbd: %s", e)

    def _initialize_clients(self) -> None:
        self._try_init_torrent()
        self._try_init_usenet()

    # ------------------------------------------------------------------
    # Health reporting
    # ------------------------------------------------------------------

    def populate_initial_health(self, registry: object) -> None:
        """
        Seed the health registry with the outcome of startup initialization.
        Call once right after creating the singleton so the UI has immediate status.
        """
        from media_manager.health.schemas import ServiceStatus

        torrent_enabled = self.config.qbittorrent.enabled or self.config.transmission.enabled
        if torrent_enabled:
            name, display = self._torrent_client_id()
            if self._torrent_client is not None:
                registry.update(name, display, ServiceStatus.healthy)  # type: ignore[attr-defined]
            else:
                registry.update(name, display, ServiceStatus.unavailable, self._torrent_error)  # type: ignore[attr-defined]

        if self.config.sabnzbd.enabled:
            name, display = self._usenet_client_id()
            if self._usenet_client is not None:
                registry.update(name, display, ServiceStatus.healthy)  # type: ignore[attr-defined]
            else:
                registry.update(name, display, ServiceStatus.unavailable, self._usenet_error)  # type: ignore[attr-defined]

    def _torrent_client_id(self) -> tuple[str, str]:
        if self._torrent_client is not None:
            return self._torrent_client.name, self._torrent_client.display_name
        if self.config.qbittorrent.enabled:
            return QbittorrentDownloadClient.name, QbittorrentDownloadClient.display_name
        return TransmissionDownloadClient.name, TransmissionDownloadClient.display_name

    def _usenet_client_id(self) -> tuple[str, str]:
        if self._usenet_client is not None:
            return self._usenet_client.name, self._usenet_client.display_name
        return SabnzbdDownloadClient.name, SabnzbdDownloadClient.display_name

    async def run_health_check(self, registry: object) -> None:
        """
        Ping all configured clients; reconnect any that are offline; update the
        health registry. Designed to be called from a periodic background task.
        """
        from media_manager.health.schemas import ServiceStatus

        torrent_enabled = self.config.qbittorrent.enabled or self.config.transmission.enabled

        if torrent_enabled:
            name, display = self._torrent_client_id()
            if self._torrent_client is not None:
                ok = await asyncio.to_thread(self._torrent_client.ping)
                if ok:
                    registry.update(name, display, ServiceStatus.healthy)  # type: ignore[attr-defined]
                else:
                    log.warning("%s is unreachable, marking unavailable", display)
                    with self._lock:
                        self._torrent_client = None
                        self._torrent_error = "Ping failed"
                    registry.update(name, display, ServiceStatus.unavailable, "Connection lost")  # type: ignore[attr-defined]
            else:
                # Try to reconnect
                await asyncio.to_thread(self._try_init_torrent)
                name, display = self._torrent_client_id()
                if self._torrent_client is not None:
                    log.info("%s reconnected successfully", display)
                    registry.update(name, display, ServiceStatus.healthy)  # type: ignore[attr-defined]
                else:
                    registry.update(name, display, ServiceStatus.unavailable, self._torrent_error)  # type: ignore[attr-defined]

        if self.config.sabnzbd.enabled:
            name, display = self._usenet_client_id()
            if self._usenet_client is not None:
                ok = await asyncio.to_thread(self._usenet_client.ping)
                if ok:
                    registry.update(name, display, ServiceStatus.healthy)  # type: ignore[attr-defined]
                else:
                    log.warning("%s is unreachable, marking unavailable", display)
                    with self._lock:
                        self._usenet_client = None
                        self._usenet_error = "Ping failed"
                    registry.update(name, display, ServiceStatus.unavailable, "Connection lost")  # type: ignore[attr-defined]
            else:
                await asyncio.to_thread(self._try_init_usenet)
                name, display = self._usenet_client_id()
                if self._usenet_client is not None:
                    log.info("%s reconnected successfully", display)
                    registry.update(name, display, ServiceStatus.healthy)  # type: ignore[attr-defined]
                else:
                    registry.update(name, display, ServiceStatus.unavailable, self._usenet_error)  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _get_appropriate_client(
        self, indexer_result: IndexerQueryResult | Torrent
    ) -> AbstractDownloadClient:
        if indexer_result.usenet:
            if not self._usenet_client:
                msg = f"Usenet client unavailable: {self._usenet_error or 'not configured'}"
                raise RuntimeError(msg)
            return self._usenet_client
        if not self._torrent_client:
            msg = f"Torrent client unavailable: {self._torrent_error or 'not configured'}"
            raise RuntimeError(msg)
        return self._torrent_client

    def download(self, indexer_result: IndexerQueryResult) -> Torrent:
        log.info("Processing download request for: %s", indexer_result.title)
        client = self._get_appropriate_client(indexer_result)
        return client.download_torrent(indexer_result)

    def remove_torrent(self, torrent: Torrent, delete_data: bool = False) -> None:
        log.info("Removing torrent: %s", torrent.title)
        client = self._get_appropriate_client(torrent)
        client.remove_torrent(torrent, delete_data)

    def get_torrent_status(self, torrent: Torrent) -> TorrentStatus:
        client = self._get_appropriate_client(torrent)
        return client.get_torrent_status(torrent)

    def pause_torrent(self, torrent: Torrent) -> None:
        log.info("Pausing torrent: %s", torrent.title)
        client = self._get_appropriate_client(torrent)
        client.pause_torrent(torrent)

    def resume_torrent(self, torrent: Torrent) -> None:
        log.info("Resuming torrent: %s", torrent.title)
        client = self._get_appropriate_client(torrent)
        client.resume_torrent(torrent)


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_instance: DownloadManager | None = None
_instance_lock = threading.Lock()


def init_download_manager() -> DownloadManager:
    """Create the singleton DownloadManager. Call once during app startup."""
    global _instance
    with _instance_lock:
        _instance = DownloadManager()
        return _instance


def get_download_manager() -> DownloadManager:
    """Return the singleton DownloadManager, creating it lazily if needed."""
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = DownloadManager()
    return _instance  # type: ignore[return-value]
