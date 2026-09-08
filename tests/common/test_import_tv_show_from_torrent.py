"""
TvService.download_torrent creates an EpisodeFile row for each episode a
torrent covers (with no relative_path yet) *before* the torrent even
finishes downloading. When the import step later runs, it must update that
same row - not insert a second one, which collides on the
(episode_id, file_path_suffix) primary key with a UniqueViolation. This was
a real bug: every plain TV import hit it, since the import path always used
the same default file_path_suffix ("") as the download path.
"""

import asyncio
from pathlib import Path

import pytest

from media_manager.config import get_config
from media_manager.torrent.schemas import Quality
from media_manager.tv.importer import TvImportService
from media_manager.tv.schemas import (
    Episode,
    EpisodeFile,
    EpisodeId,
    EpisodeNumber,
    Season,
    SeasonNumber,
    Show,
)


class FakeTvRepository:
    """
    Mimics the real repository's primary-key semantics closely enough to
    catch the regression: add_episode_file raises on a duplicate
    (episode_id, file_path_suffix), exactly like the DB's unique constraint.
    """

    def __init__(self, season: Season) -> None:
        self.season = season
        self.episode_files: list[EpisodeFile] = []

    async def get_season_by_number(self, season_number: int, show_id: object) -> Season:  # noqa: ARG002
        return self.season

    async def set_episode_file_relative_path(
        self, episode_id: EpisodeId, file_path_suffix: str, relative_path: str | None
    ) -> bool:
        updated = False
        for file in self.episode_files:
            if (
                file.episode_id == episode_id
                and file.file_path_suffix == file_path_suffix
            ):
                file.relative_path = relative_path
                updated = True
        return updated

    async def add_episode_file(self, episode_file: EpisodeFile) -> EpisodeFile:
        for file in self.episode_files:
            if (
                file.episode_id == episode_file.episode_id
                and file.file_path_suffix == episode_file.file_path_suffix
            ):
                msg = (
                    'duplicate key value violates unique constraint "episode_file_pkey"'
                )
                raise RuntimeError(msg)
        self.episode_files.append(episode_file)
        return episode_file


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


def test_importing_a_torrent_updates_the_download_time_record_in_place(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("MEDIAMANAGER_MISC__TV_DIRECTORY", str(tmp_path / "library"))
    show, season = _show_with_one_episode()
    episode = season.episodes[0]

    repository = FakeTvRepository(season=season)
    # The row download_torrent already created, before the torrent finished.
    repository.episode_files.append(
        EpisodeFile(
            episode_id=episode.id,
            quality=Quality.fullhd,
            torrent_id=None,
            file_path_suffix="",
            relative_path=None,
        )
    )

    service = TvImportService(
        tv_repository=repository,
        torrent_service=None,
        notification_service=None,
        tv_metadata_service=None,
    )

    source_directory = tmp_path / "downloaded"
    source_directory.mkdir()
    (source_directory / "The.Show.S01E01.mkv").write_bytes(b"data")

    success, error_msg = asyncio.run(
        service.import_tv_show(
            show=show,
            source_directory=source_directory,
            quality=Quality.fullhd,
            torrent_id=None,
        )
    )

    assert error_msg is None
    assert success is True
    # Updated in place, not duplicated.
    assert len(repository.episode_files) == 1
    assert repository.episode_files[0].relative_path is not None
