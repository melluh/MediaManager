"""
A torrent seen to have finished downloading must be imported right away,
rather than sitting on "Waiting for import" until the next cron run.
"""

import asyncio

import pytest

from media_manager.torrent import service as torrent_service_module
from media_manager.torrent.schemas import (
    DownloadProgress,
    DownloadState,
    Torrent,
    TorrentStatus,
)
from media_manager.torrent.service import TorrentService


class FakeTorrentRepository:
    async def save_torrent(self, torrent: Torrent) -> Torrent:
        return torrent


class FakeDownloadManager:
    def __init__(
        self, status: TorrentStatus, progress: DownloadProgress | None = None
    ) -> None:
        self._status = status
        self._progress = progress

    def get_torrent_status(self, _torrent: Torrent) -> TorrentStatus:
        return self._status

    def get_download_progress_bulk(
        self, torrents: list[Torrent]
    ) -> dict[str, DownloadProgress]:
        if self._progress is None:
            return {}
        return {t.hash: self._progress for t in torrents}


@pytest.fixture
def enqueued(monkeypatch: pytest.MonkeyPatch) -> list[None]:
    calls: list[None] = []

    async def fake_enqueue() -> None:
        calls.append(None)

    monkeypatch.setattr(torrent_service_module, "_enqueue_torrent_imports", fake_enqueue)
    return calls


def _torrent(status: TorrentStatus) -> Torrent:
    return Torrent(status=status, title="Some Movie 2024", imported=False, hash="abc")


def _service(download_manager: FakeDownloadManager) -> TorrentService:
    return TorrentService(
        torrent_repository=FakeTorrentRepository(),
        download_manager=download_manager,
    )


def test_status_check_enqueues_import_when_torrent_finishes(enqueued):
    service = _service(FakeDownloadManager(TorrentStatus.finished))

    asyncio.run(service.get_torrent_status(_torrent(TorrentStatus.downloading)))

    assert len(enqueued) == 1


def test_status_check_does_not_enqueue_while_still_downloading(enqueued):
    service = _service(FakeDownloadManager(TorrentStatus.downloading))

    asyncio.run(service.get_torrent_status(_torrent(TorrentStatus.downloading)))

    assert enqueued == []


def test_already_finished_torrent_does_not_enqueue_again(enqueued):
    service = _service(FakeDownloadManager(TorrentStatus.finished))

    asyncio.run(service.get_torrent_status(_torrent(TorrentStatus.finished)))

    assert enqueued == []


def test_progress_polling_enqueues_import_when_torrent_finishes(enqueued):
    progress = DownloadProgress(state=DownloadState.seeding, progress=100)
    service = _service(FakeDownloadManager(TorrentStatus.finished, progress))

    asyncio.run(service.enrich_torrents([_torrent(TorrentStatus.downloading)]))

    assert len(enqueued) == 1


def test_enqueue_failure_does_not_break_status_check(monkeypatch):
    async def failing_enqueue() -> None:
        msg = "broker unavailable"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        torrent_service_module, "_enqueue_torrent_imports", failing_enqueue
    )
    service = _service(FakeDownloadManager(TorrentStatus.finished))

    torrent = asyncio.run(
        service.get_torrent_status(_torrent(TorrentStatus.downloading))
    )

    assert torrent.status == TorrentStatus.finished
