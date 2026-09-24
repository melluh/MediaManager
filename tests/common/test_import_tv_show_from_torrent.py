"""
A download no longer creates EpisodeFile rows up front - it only links the
torrent to its episodes (EpisodeDownload), with the file path suffix the
files are to be imported as. The import is what creates each file row, once
the file is on disk, under that suffix; importing over a file already
recorded for the same episode and suffix replaces its record rather than
colliding on the (episode_id, file_path_suffix) primary key.
"""

import asyncio
import uuid
from pathlib import Path

import pytest

from media_manager.config import get_config
from media_manager.torrent.schemas import Torrent, TorrentStatus
from media_manager.tv.importer import TvImportService
from media_manager.tv.schemas import (
    Episode,
    EpisodeDownload,
    EpisodeFile,
    EpisodeNumber,
    Season,
    SeasonNumber,
    Show,
)


class FakeTvRepository:
    """Mimics the real repository's upsert on (episode_id, file_path_suffix)."""

    def __init__(self, season: Season) -> None:
        self.season = season
        self.episode_files: list[EpisodeFile] = []

    async def get_season_by_number(self, season_number: int, show_id: object) -> Season:  # noqa: ARG002
        return self.season

    async def upsert_episode_file(self, episode_file: EpisodeFile) -> None:
        self.episode_files = [
            file
            for file in self.episode_files
            if (file.episode_id, file.file_path_suffix)
            != (episode_file.episode_id, episode_file.file_path_suffix)
        ]
        self.episode_files.append(episode_file.model_copy())

    async def update_episode_file_details(self, episode_files: list[EpisodeFile]) -> None:
        for changed in episode_files:
            for file in self.episode_files:
                if (file.episode_id, file.file_path_suffix) == (
                    changed.episode_id,
                    changed.file_path_suffix,
                ):
                    file.details = changed.details
                    file.probed_mtime_ns = changed.probed_mtime_ns


class FakeTorrentRepository:
    def __init__(self) -> None:
        self.saved: list[Torrent] = []

    async def save_torrent(self, torrent: Torrent) -> Torrent:
        self.saved.append(torrent)
        return torrent


class FakeTorrentService:
    def __init__(self, downloads: list[EpisodeDownload]) -> None:
        self.downloads = downloads
        self.torrent_repository = FakeTorrentRepository()

    async def get_episode_downloads_of_torrent(
        self,
        torrent: Torrent,  # noqa: ARG002
    ) -> list[EpisodeDownload]:
        return self.downloads


@pytest.fixture(autouse=True)
def _uncached_config():
    get_config.cache_clear()
    yield
    get_config.cache_clear()


def _show_with_one_episode() -> tuple[Show, Season]:
    episode = Episode(number=EpisodeNumber(1), external_id=1, title="Episode 1")
    season = Season(
        number=SeasonNumber(1),
        name="Season 1",
        overview="",
        external_id=1,
        episodes=[episode],
    )
    show = Show(
        name="The Show",
        overview="",
        year=2005,
        external_id=1,
        metadata_provider="tvdb",
        seasons=[season],
    )
    return show, season


def _import(tmp_path: Path, monkeypatch, repository, torrent_service, show) -> Torrent:
    monkeypatch.setenv("MEDIAMANAGER_MISC__TV_DIRECTORY", str(tmp_path / "library"))
    monkeypatch.setenv("MEDIAMANAGER_MISC__TORRENT_DIRECTORY", str(tmp_path / "torrents"))
    torrent = Torrent(status=TorrentStatus.finished, title="The.Show.S01E01", hash="x")
    source_directory = tmp_path / "torrents" / "The.Show.S01E01"
    source_directory.mkdir(parents=True)
    (source_directory / "The.Show.S01E01.mkv").write_bytes(b"data")

    service = TvImportService(
        tv_repository=repository,
        torrent_service=torrent_service,
        notification_service=None,
        tv_metadata_service=None,
    )
    asyncio.run(service.import_torrent_files(torrent=torrent, show=show))
    return torrent


def test_importing_a_torrent_records_its_files_under_the_download_suffix(
    tmp_path: Path, monkeypatch
):
    show, season = _show_with_one_episode()
    episode = season.episodes[0]
    repository = FakeTvRepository(season=season)
    torrent_service = FakeTorrentService(
        downloads=[
            EpisodeDownload(
                torrent_id=uuid.uuid4(), episode_id=episode.id, file_path_suffix="WEB"
            )
        ]
    )

    torrent = _import(tmp_path, monkeypatch, repository, torrent_service, show)

    assert torrent.imported is True
    [episode_file] = repository.episode_files
    assert episode_file.episode_id == episode.id
    assert episode_file.file_path_suffix == "WEB"
    assert episode_file.torrent_id == torrent.id
    assert episode_file.relative_path == "Season 1/The Show - S01E01 - WEB.mkv"
    # Probed right away, so the file shows up with its details.
    assert episode_file.details is not None
    assert episode_file.details.size_bytes == 4


def test_importing_over_an_existing_file_replaces_its_record(
    tmp_path: Path, monkeypatch
):
    show, season = _show_with_one_episode()
    episode = season.episodes[0]
    repository = FakeTvRepository(season=season)
    repository.episode_files.append(
        EpisodeFile(
            episode_id=episode.id,
            torrent_id=None,
            file_path_suffix="",
            relative_path="Season 1/Old Name.mkv",
        )
    )
    torrent_service = FakeTorrentService(
        downloads=[
            EpisodeDownload(
                torrent_id=uuid.uuid4(), episode_id=episode.id, file_path_suffix=""
            )
        ]
    )

    _import(tmp_path, monkeypatch, repository, torrent_service, show)

    assert [file.relative_path for file in repository.episode_files] == [
        "Season 1/The Show - S01E01.mkv"
    ]
