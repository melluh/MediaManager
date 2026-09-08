"""
BaseMediaService.import_all_torrents_base must leave a visible trace when
importing a torrent raises unexpectedly - otherwise the torrent just retries
the same failure every cron pass forever, stuck on "Waiting for import" with
nothing in the UI to show why.
"""

import asyncio

import pytest

from media_manager.movies.importer import MovieImportService
from media_manager.torrent.schemas import Quality, Torrent, TorrentStatus


class FakeTorrentRepository:
    def __init__(self) -> None:
        self.saved: list[Torrent] = []

    async def save_torrent(self, torrent: Torrent) -> Torrent:
        self.saved.append(torrent)
        return torrent


class FakeTorrentService:
    def __init__(self, torrents: list[Torrent]) -> None:
        self._torrents = torrents
        self.torrent_repository = FakeTorrentRepository()

    async def get_completed_torrents(self) -> list[Torrent]:
        return self._torrents


def _torrent() -> Torrent:
    return Torrent(
        status=TorrentStatus.finished,
        title="Some Movie 2024",
        quality=Quality.unknown,
        imported=False,
        hash="deadbeef",
    )


@pytest.fixture(autouse=True)
def _uncached_config():
    from media_manager.config import get_config

    get_config.cache_clear()
    yield
    get_config.cache_clear()


def test_an_unexpected_exception_is_recorded_as_an_import_error():
    torrent = _torrent()
    torrent_service = FakeTorrentService([torrent])
    service = MovieImportService(
        movie_repository=None,
        torrent_service=torrent_service,
        notification_service=None,
        movie_metadata_service=None,
    )

    async def get_media_func(_torrent: Torrent) -> None:
        msg = "disk unavailable"
        raise RuntimeError(msg)

    async def import_torrent_func(_torrent: Torrent, _media: None) -> None:
        pytest.fail("must not be called when get_media_func raises")

    asyncio.run(
        service.import_all_torrents_base(
            get_media_func=get_media_func,
            import_torrent_func=import_torrent_func,
            media_type_name="movie",
        )
    )

    assert len(torrent_service.torrent_repository.saved) == 1
    saved = torrent_service.torrent_repository.saved[0]
    assert saved.imported is False
    assert saved.import_error == "RuntimeError: disk unavailable"
