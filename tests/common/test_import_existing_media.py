"""
Importing media that is already on disk: the media item is pointed at the
directory the user already has and the files in it are recorded where they
lie. Nothing is copied, hardlinked or moved.
"""

import asyncio
import json
from pathlib import Path

import pytest

from media_manager.common.import_sidecar import (
    SIDECAR_FILENAME,
    read_import_sidecar,
)
from media_manager.config import get_config
from media_manager.exceptions import ConflictError
from media_manager.movies.importer import MovieImportService
from media_manager.movies.schemas import Movie, MovieFile, MovieId
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
    ShowId,
)


class FakeMovieRepository:
    def __init__(self) -> None:
        self.movie_files: list[MovieFile] = []
        self.directory_name: str | None = None

    async def get_movie_files_by_movie_id(self, movie_id: MovieId) -> list[MovieFile]:
        return [file for file in self.movie_files if file.movie_id == movie_id]

    async def set_directory_name(self, entity_id: MovieId, directory_name: str) -> None:  # noqa: ARG002
        self.directory_name = directory_name

    async def add_movie_file(self, movie_file: MovieFile) -> MovieFile:
        self.movie_files.append(movie_file)
        return movie_file

    async def set_movie_file_relative_path(
        self, movie_id: MovieId, file_path_suffix: str, relative_path: str | None
    ) -> None:
        for file in self.movie_files:
            if file.movie_id == movie_id and file.file_path_suffix == file_path_suffix:
                file.relative_path = relative_path


class FakeTvRepository:
    def __init__(self) -> None:
        self.episode_files: list[EpisodeFile] = []
        self.directory_name: str | None = None

    async def get_episode_files_by_show_id(
        self,
        show_id: ShowId,  # noqa: ARG002
    ) -> dict[EpisodeId, list[EpisodeFile]]:
        grouped: dict[EpisodeId, list[EpisodeFile]] = {}
        for file in self.episode_files:
            grouped.setdefault(file.episode_id, []).append(file)
        return grouped

    async def set_directory_name(self, entity_id: ShowId, directory_name: str) -> None:  # noqa: ARG002
        self.directory_name = directory_name

    async def add_episode_file(self, episode_file: EpisodeFile) -> EpisodeFile:
        self.episode_files.append(episode_file)
        return episode_file

    async def set_episode_file_relative_path(
        self, episode_id: EpisodeId, file_path_suffix: str, relative_path: str | None
    ) -> None:
        for file in self.episode_files:
            if (
                file.episode_id == episode_id
                and file.file_path_suffix == file_path_suffix
            ):
                file.relative_path = relative_path


@pytest.fixture(autouse=True)
def _uncached_config():
    """
    The services resolve their root directory from the cached config, which
    must not carry one test's temporary library into the next.
    """
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


def _show(episodes_by_season: dict[int, list[int]]) -> Show:
    return Show(
        name="The Show",
        overview="",
        year=2005,
        external_id=1,
        metadata_provider="tvdb",
        seasons=[
            Season(
                number=SeasonNumber(season_number),
                name=f"Season {season_number}",
                overview="",
                external_id=season_number,
                episodes=[
                    Episode(
                        number=EpisodeNumber(episode_number),
                        external_id=episode_number,
                        title=f"Episode {episode_number}",
                    )
                    for episode_number in episode_numbers
                ],
            )
            for season_number, episode_numbers in episodes_by_season.items()
        ],
    )


def _movie_service(library: Path, monkeypatch) -> tuple[MovieImportService, FakeMovieRepository]:
    monkeypatch.setenv("MEDIAMANAGER_MISC__MOVIE_DIRECTORY", str(library))
    repository = FakeMovieRepository()
    service = MovieImportService(
        movie_repository=repository,
        torrent_service=None,
        notification_service=None,
        movie_metadata_service=None,
    )
    return service, repository


def _tv_service(library: Path, monkeypatch) -> tuple[TvImportService, FakeTvRepository]:
    monkeypatch.setenv("MEDIAMANAGER_MISC__TV_DIRECTORY", str(library))
    repository = FakeTvRepository()
    service = TvImportService(
        tv_repository=repository,
        torrent_service=None,
        notification_service=None,
        tv_metadata_service=None,
    )
    return service, repository


def _touch(path: Path, content: bytes = b"video") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _snapshot(root: Path) -> dict[str, bytes]:
    """
    Every media file under a directory with its contents, to compare
    before/after. The import-match sidecar an import writes is deliberately
    new, so it is not part of what has to stay untouched.
    """
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.name != SIDECAR_FILENAME
    }


def test_importing_a_movie_records_it_where_it_already_lies(tmp_path, monkeypatch):
    library = tmp_path / "movies"
    source = _touch(library / "Some Movie (2024)" / "some.movie.1080p.mkv").parent
    service, repository = _movie_service(library, monkeypatch)
    before = _snapshot(library)

    imported = asyncio.run(
        service.import_existing_movie(movie=_movie(), source_directory=source)
    )

    assert imported
    assert repository.directory_name == "Some Movie (2024)"
    assert [
        (file.file_path_suffix, file.relative_path) for file in repository.movie_files
    ] == [("some.movie.1080p", "some.movie.1080p.mkv")]
    # Nothing was copied, hardlinked or moved: the library is byte for byte
    # what it was, with no second directory next to the original.
    assert _snapshot(library) == before
    assert [path.name for path in library.iterdir()] == ["Some Movie (2024)"]
    # The directory belongs to the movie now, so later scans skip it and its
    # cached match is removed rather than left behind in the user's library.
    assert read_import_sidecar(source) is None


def test_importing_a_show_adopts_episodes_from_a_hand_made_layout(
    tmp_path, monkeypatch
):
    library = tmp_path / "tv"
    source = library / "Some Show"
    _touch(source / "Season 01" / "Some Show - S01E01.mkv")
    _touch(source / "S01" / "some.show.s01e02.mkv")
    _touch(source / "Some Show - S02E01.mkv")
    service, repository = _tv_service(library, monkeypatch)
    show = _show({1: [1, 2], 2: [1]})
    before = _snapshot(library)

    imported = asyncio.run(
        service.import_existing_tv_show(tv_show=show, source_directory=source)
    )

    assert imported
    assert repository.directory_name == "Some Show"
    assert sorted(file.relative_path for file in repository.episode_files) == [
        "S01/some.show.s01e02.mkv",
        "Season 01/Some Show - S01E01.mkv",
        "Some Show - S02E01.mkv",
    ]
    assert _snapshot(library) == before
    assert [path.name for path in library.iterdir()] == ["Some Show"]


def test_importing_a_show_ignores_a_file_naming_an_unknown_episode(
    tmp_path, monkeypatch
):
    library = tmp_path / "tv"
    source = library / "Some Show"
    _touch(source / "Some Show - S01E01.mkv")
    _touch(source / "Some Show - S09E99.mkv")
    _touch(source / "behind the scenes.mkv")
    service, repository = _tv_service(library, monkeypatch)

    imported = asyncio.run(
        service.import_existing_tv_show(
            tv_show=_show({1: [1]}), source_directory=source
        )
    )

    assert imported
    assert [file.relative_path for file in repository.episode_files] == [
        "Some Show - S01E01.mkv"
    ]


def test_importing_a_movie_that_already_has_files_is_refused(tmp_path, monkeypatch):
    library = tmp_path / "movies"
    source = _touch(library / "Some Movie (2024)" / "some.movie.mkv").parent
    service, repository = _movie_service(library, monkeypatch)
    movie = _movie()
    repository.movie_files.append(
        MovieFile(
            movie_id=movie.id,
            quality=Quality.unknown,
            torrent_id=None,
            file_path_suffix="",
            relative_path="The Movie (2024).mkv",
        )
    )

    with pytest.raises(ConflictError):
        asyncio.run(
            service.import_existing_movie(movie=movie, source_directory=source)
        )

    # Re-pointing the directory would have orphaned the existing record.
    assert repository.directory_name is None


def test_importing_a_show_that_already_has_files_is_refused(tmp_path, monkeypatch):
    library = tmp_path / "tv"
    source = library / "Some Show"
    _touch(source / "Some Show - S01E01.mkv")
    service, repository = _tv_service(library, monkeypatch)
    show = _show({1: [1]})
    repository.episode_files.append(
        EpisodeFile(
            episode_id=show.seasons[0].episodes[0].id,
            quality=Quality.unknown,
            torrent_id=None,
            file_path_suffix="",
            relative_path="Season 1/The Show - S01E01.mkv",
        )
    )

    with pytest.raises(ConflictError):
        asyncio.run(
            service.import_existing_tv_show(tv_show=show, source_directory=source)
        )

    assert repository.directory_name is None


def test_importing_a_directory_with_no_video_files_reports_failure(
    tmp_path, monkeypatch
):
    library = tmp_path / "movies"
    source = _touch(library / "Some Movie (2024)" / "readme.txt").parent
    service, _ = _movie_service(library, monkeypatch)

    imported = asyncio.run(
        service.import_existing_movie(movie=_movie(), source_directory=source)
    )

    assert not imported


def test_a_second_import_scan_of_an_imported_movie_changes_nothing(
    tmp_path, monkeypatch
):
    library = tmp_path / "movies"
    source = _touch(library / "Some Movie (2024)" / "some.movie.mkv").parent
    service, repository = _movie_service(library, monkeypatch)
    movie = _movie()

    asyncio.run(service.import_existing_movie(movie=movie, source_directory=source))
    imported_files = [file.model_copy() for file in repository.movie_files]

    plan = asyncio.run(
        service.scan_movie_files(
            movie=movie.model_copy(update={"directory_name": source.name})
        )
    )

    assert plan.relinked == []
    assert plan.cleared == []
    assert plan.adoptions == []
    assert repository.movie_files == imported_files


def test_a_movie_whose_directory_is_missing_is_left_untouched(tmp_path, monkeypatch):
    library = tmp_path / "movies"
    library.mkdir()
    service, repository = _movie_service(library, monkeypatch)
    movie = _movie().model_copy(update={"directory_name": "not-mounted"})
    repository.movie_files.append(
        MovieFile(
            movie_id=movie.id,
            quality=Quality.unknown,
            torrent_id=None,
            file_path_suffix="",
            relative_path="The Movie (2024).mkv",
        )
    )

    plan = asyncio.run(service.scan_movie_files(movie=movie))

    assert plan.skipped
    assert repository.movie_files[0].relative_path == "The Movie (2024).mkv"


def test_importing_into_a_mismatched_library_is_refused(tmp_path, monkeypatch):
    # The source always sits in the default root, but a media item's parent
    # directory comes from its assigned library. When those disagree the scan
    # would look somewhere that does not exist, so the import must refuse
    # rather than store a directory name pointing nowhere.
    library = tmp_path / "movies"
    source = _touch(library / "Some Movie (2024)" / "some.movie.mkv").parent
    monkeypatch.setenv(
        "MEDIAMANAGER_MISC__MOVIE_LIBRARIES",
        json.dumps([{"name": "Elsewhere", "path": str(tmp_path / "elsewhere")}]),
    )
    service, repository = _movie_service(library, monkeypatch)
    movie = _movie().model_copy(update={"library": "Elsewhere"})

    with pytest.raises(ConflictError):
        asyncio.run(
            service.import_existing_movie(movie=movie, source_directory=source)
        )

    assert repository.directory_name is None
