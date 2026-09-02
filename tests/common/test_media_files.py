import asyncio
from pathlib import Path

from media_manager.common.media_files import (
    MediaFileLocation,
    attach_media_file_details,
    episode_file_stem,
    locate_media_file,
    media_directory_name,
    movie_file_stem,
    season_directory_name,
)
from media_manager.common.schemas import PublicMediaFile
from media_manager.torrent.schemas import Quality


def _public_file(
    file_path_suffix: str = "", relative_path: str | None = None
) -> PublicMediaFile:
    return PublicMediaFile(
        quality=Quality.unknown,
        torrent_id=None,
        file_path_suffix=file_path_suffix,
        relative_path=relative_path,
    )


def test_movie_file_stem():
    assert movie_file_stem("The Movie", 2024) == "The Movie (2024)"
    assert movie_file_stem("The Movie", 2024, "1080p") == "The Movie (2024) - 1080p"


def test_episode_file_stem():
    assert episode_file_stem("The Show", 1, 2) == "The Show - S01E02"
    assert (
        episode_file_stem("The Show", 1, 2, "IMPORTED")
        == "The Show - S01E02 - IMPORTED"
    )


def test_media_directory_name():
    assert (
        media_directory_name("The Movie", 2024, "tmdb", 451915)
        == "The Movie (2024) [tmdbid-451915]"
    )
    assert (
        media_directory_name("The Show", 2005, "tvdb", 73255)
        == "The Show (2005) [tvdbid-73255]"
    )


def test_media_directory_name_without_a_year():
    assert (
        media_directory_name("The Movie", None, "tmdb", 451915)
        == "The Movie [tmdbid-451915]"
    )


def test_media_directory_name_sanitizes_only_the_name():
    # The directory names already on disk were built this way; the bracketed
    # id group must survive verbatim so they keep matching.
    assert (
        media_directory_name("Wall-E: A Story?", 2008, "tmdb", 10681)
        == "Wall-E A Story (2008) [tmdbid-10681]"
    )


def test_season_directory_name():
    assert season_directory_name(3) == "Season 3"


def test_locate_media_file_prefers_video_over_subtitle(tmp_path: Path):
    (tmp_path / "The Movie (2024).en.srt").touch()
    (tmp_path / "The Movie (2024).mkv").touch()

    located = locate_media_file(
        MediaFileLocation(
            directory=tmp_path,
            stem="The Movie (2024)",
            relative_to=tmp_path.parent,
            media_root=tmp_path,
        )
    )

    assert located == tmp_path / "The Movie (2024).mkv"


def test_locate_media_file_does_not_match_a_longer_stem(tmp_path: Path):
    # A suffixed file belongs to a different file record and must not be
    # served up as the unsuffixed one's file.
    (tmp_path / "The Movie (2024) - 1080p.mkv").touch()

    located = locate_media_file(
        MediaFileLocation(
            directory=tmp_path,
            stem="The Movie (2024)",
            relative_to=tmp_path.parent,
            media_root=tmp_path,
        )
    )

    assert located is None


def test_locate_media_file_returns_none_for_missing_directory(tmp_path: Path):
    assert (
        locate_media_file(
            MediaFileLocation(
                directory=tmp_path / "nope",
                stem="x",
                relative_to=tmp_path,
                media_root=tmp_path / "nope",
            )
        )
        is None
    )


def test_attach_media_file_details_reports_path_and_size(tmp_path: Path):
    movie_dir = tmp_path / "The Movie (2024)"
    movie_dir.mkdir()
    (movie_dir / "The Movie (2024).mkv").write_bytes(b"12345")

    file = _public_file()
    asyncio.run(
        attach_media_file_details(
            [file],
            [
                MediaFileLocation(
                    directory=movie_dir,
                    stem="The Movie (2024)",
                    relative_to=tmp_path,
                    media_root=movie_dir,
                )
            ],
        )
    )

    assert file.exists_on_disk is True
    assert file.file_path == str(Path("The Movie (2024)") / "The Movie (2024).mkv")
    assert file.details is not None
    assert file.details.size_bytes == 5


def test_attach_media_file_details_falls_back_to_expected_path(tmp_path: Path):
    file = _public_file()
    asyncio.run(
        attach_media_file_details(
            [file],
            [
                MediaFileLocation(
                    directory=tmp_path / "The Movie (2024)",
                    stem="The Movie (2024)",
                    relative_to=tmp_path,
                    media_root=tmp_path / "The Movie (2024)",
                )
            ],
        )
    )

    assert file.exists_on_disk is False
    assert file.details is None
    assert file.file_path == str(Path("The Movie (2024)") / "The Movie (2024)")


def test_attach_media_file_details_prefers_a_stored_relative_path(tmp_path: Path):
    show_dir = tmp_path / "The Show (2005) [tmdbid-1]"
    season_dir = show_dir / "Season 1"
    season_dir.mkdir(parents=True)
    (season_dir / "Renamed Episode.mkv").write_bytes(b"123")

    file = _public_file(relative_path="Season 1/Renamed Episode.mkv")
    asyncio.run(
        attach_media_file_details(
            [file],
            [
                MediaFileLocation(
                    directory=season_dir,
                    stem="The Show - S01E01",
                    relative_to=tmp_path,
                    media_root=show_dir,
                )
            ],
        )
    )

    assert file.exists_on_disk is True
    assert file.details is not None
    assert file.details.size_bytes == 3
    assert file.file_path == str(
        Path("The Show (2005) [tmdbid-1]") / "Season 1" / "Renamed Episode.mkv"
    )


def test_attach_media_file_details_reports_a_missing_stored_relative_path(
    tmp_path: Path,
):
    file = _public_file(relative_path="Season 1/Gone.mkv")
    asyncio.run(
        attach_media_file_details(
            [file],
            [
                MediaFileLocation(
                    directory=tmp_path / "Season 1",
                    stem="The Show - S01E01",
                    relative_to=tmp_path.parent,
                    media_root=tmp_path,
                )
            ],
        )
    )

    assert file.exists_on_disk is False
    assert file.details is None
    assert file.file_path.endswith(str(Path("Season 1") / "Gone.mkv"))
