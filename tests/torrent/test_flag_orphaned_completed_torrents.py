"""
A torrent can end up linked to no movie or show at all - the media (or its
file record) was deleted without also removing the torrent, or the file-record
insert failed after the torrent's own row was already committed. Without
flagging it, such a torrent retries "Waiting for import" forever with nothing
in the UI to show why.
"""

import asyncio

from media_manager.movies.schemas import Movie
from media_manager.torrent.schemas import Quality, Torrent, TorrentId, TorrentStatus
from media_manager.torrent.service import TorrentService


class FakeTorrentRepository:
    def __init__(
        self,
        torrents: list[Torrent],
        movies_by_torrent_id: dict[TorrentId, Movie] | None = None,
    ) -> None:
        self._torrents = torrents
        self._movies_by_torrent_id = movies_by_torrent_id or {}
        self.saved: list[Torrent] = []

    async def get_all_torrents(self) -> list[Torrent]:
        return self._torrents

    async def get_movies_of_torrents(
        self, torrent_ids: list[TorrentId]
    ) -> dict[TorrentId, Movie]:
        return {
            tid: movie
            for tid, movie in self._movies_by_torrent_id.items()
            if tid in torrent_ids
        }

    async def get_shows_of_torrents(self, torrent_ids: list[TorrentId]) -> dict:  # noqa: ARG002
        return {}

    async def save_torrent(self, torrent: Torrent) -> Torrent:
        self.saved.append(torrent)
        return torrent


def _torrent(title: str) -> Torrent:
    return Torrent(
        status=TorrentStatus.finished,
        title=title,
        quality=Quality.unknown,
        imported=False,
        hash=title,
    )


def test_a_torrent_with_no_linked_media_is_flagged_as_failed():
    orphan = _torrent("Orphaned Torrent")
    linked = _torrent("Linked Torrent")
    movie = Movie(
        name="The Movie",
        overview="",
        year=2024,
        external_id=1,
        metadata_provider="tmdb",
    )
    repository = FakeTorrentRepository(
        torrents=[orphan, linked],
        movies_by_torrent_id={linked.id: movie},
    )
    service = TorrentService(torrent_repository=repository, download_manager=object())

    asyncio.run(service.flag_orphaned_completed_torrents())

    assert len(repository.saved) == 1
    assert repository.saved[0].id == orphan.id
    assert repository.saved[0].import_error is not None
    assert linked.import_error is None
