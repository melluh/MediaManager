"""
A torrent records which quality slot it was downloaded for, instead of a
quality guessed from the release title - the file's actual quality is probed
once it's imported.
"""

import asyncio

from media_manager.indexer.schemas import IndexerQueryResult
from media_manager.torrent.schemas import Torrent, TorrentStatus
from media_manager.torrent.service import TorrentService


class FakeDownloadManager:
    def download(self, indexer_result: IndexerQueryResult) -> Torrent:
        return Torrent(
            status=TorrentStatus.downloading,
            title=indexer_result.title,
            hash="abc",
        )


class FakeTorrentRepository:
    async def save_torrent(self, torrent: Torrent) -> Torrent:
        return torrent


def _result(slot_label: str | None) -> IndexerQueryResult:
    return IndexerQueryResult(
        title="The.Movie.2024.1080p.WEB-DL.x264-GRP",
        download_url="magnet:?xt=urn:btih:x",
        seeders=10,
        flags=[],
        size=1,
        usenet=False,
        age=0,
        indexer="test",
        slot_label=slot_label,
    )


def _download(result: IndexerQueryResult) -> Torrent:
    service = TorrentService(
        torrent_repository=FakeTorrentRepository(),
        download_manager=FakeDownloadManager(),
    )
    return asyncio.run(service.download(indexer_result=result))


def test_a_download_records_the_slot_its_release_matched():
    torrent = _download(_result("1080p Encode"))

    assert torrent.slot == "1080p Encode"
    assert torrent.imported is False


def test_a_release_matching_no_slot_records_none():
    # No slot label from the search, and no classified attributes to
    # resolve one from.
    assert _download(_result(None)).slot is None
