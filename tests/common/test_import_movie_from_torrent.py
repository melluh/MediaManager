"""
A movie download only links the torrent to the movie (MovieDownload) - the
MovieFile row is created by the import, once the file is actually on disk,
under the file path suffix the download was started with.
"""

import asyncio
import uuid
from pathlib import Path

import pytest

from media_manager.config import get_config
from media_manager.movies.importer import MovieImportService
from media_manager.movies.schemas import Movie, MovieDownload, MovieFile
from media_manager.torrent.schemas import Torrent, TorrentStatus


class FakeMovieRepository:
    """Mimics the real repository's upsert on (movie_id, file_path_suffix)."""

    def __init__(self) -> None:
        self.movie_files: list[MovieFile] = []

    async def upsert_movie_file(self, movie_file: MovieFile) -> None:
        self.movie_files = [
            file
            for file in self.movie_files
            if (file.movie_id, file.file_path_suffix)
            != (movie_file.movie_id, movie_file.file_path_suffix)
        ]
        self.movie_files.append(movie_file.model_copy())

    async def update_movie_file_details(self, movie_files: list[MovieFile]) -> None:
        for changed in movie_files:
            for file in self.movie_files:
                if (file.movie_id, file.file_path_suffix) == (
                    changed.movie_id,
                    changed.file_path_suffix,
                ):
                    file.details = changed.details
                    file.probed_mtime_ns = changed.probed_mtime_ns


class FakeTorrentRepository:
    async def save_torrent(self, torrent: Torrent) -> Torrent:
        return torrent


class FakeTorrentService:
    def __init__(self, downloads: list[MovieDownload]) -> None:
        self.downloads = downloads
        self.torrent_repository = FakeTorrentRepository()

    async def get_movie_downloads_of_torrent(
        self,
        torrent: Torrent,  # noqa: ARG002
    ) -> list[MovieDownload]:
        return self.downloads


@pytest.fixture(autouse=True)
def _uncached_config():
    get_config.cache_clear()
    yield
    get_config.cache_clear()


def _movie() -> Movie:
    return Movie(
        name="The Movie",
        overview="",
        year=2024,
        external_id=1,
        metadata_provider="tmdb",
    )


def _import(
    tmp_path: Path, monkeypatch, downloads: list[MovieDownload], movie: Movie
) -> tuple[Torrent, FakeMovieRepository]:
    monkeypatch.setenv("MEDIAMANAGER_MISC__MOVIE_DIRECTORY", str(tmp_path / "library"))
    monkeypatch.setenv("MEDIAMANAGER_MISC__TORRENT_DIRECTORY", str(tmp_path / "torrents"))
    torrent = Torrent(status=TorrentStatus.finished, title="The.Movie.2024", hash="x")
    source_directory = tmp_path / "torrents" / "The.Movie.2024"
    source_directory.mkdir(parents=True)
    (source_directory / "The.Movie.2024.mkv").write_bytes(b"data")

    repository = FakeMovieRepository()
    service = MovieImportService(
        movie_repository=repository,
        torrent_service=FakeTorrentService(downloads),
        notification_service=None,
        movie_metadata_service=None,
    )
    asyncio.run(service.import_torrent_files(torrent=torrent, movie=movie))
    return torrent, repository


def test_importing_a_torrent_records_the_file_under_the_download_suffix(
    tmp_path: Path, monkeypatch
):
    movie = _movie()
    downloads = [
        MovieDownload(
            torrent_id=uuid.uuid4(), movie_id=movie.id, file_path_suffix="1080p Encode"
        )
    ]

    torrent, repository = _import(tmp_path, monkeypatch, downloads, movie)

    assert torrent.imported is True
    [movie_file] = repository.movie_files
    assert movie_file.file_path_suffix == "1080p Encode"
    assert movie_file.torrent_id == torrent.id
    assert movie_file.relative_path == "The Movie (2024) - 1080p Encode.mkv"
    # Probed right away, so the file shows up with its details.
    assert movie_file.details is not None
    assert movie_file.details.size_bytes == 4


def test_a_torrent_linked_to_no_movie_records_no_file(tmp_path: Path, monkeypatch):
    torrent, repository = _import(tmp_path, monkeypatch, [], _movie())

    assert torrent.imported is False
    assert torrent.import_error is not None
    assert repository.movie_files == []
