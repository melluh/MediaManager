import asyncio
from pathlib import Path

from media_manager.common.media_files import (
    DirectoryEntry,
    MediaFileLocation,
    attach_media_file_details,
    episode_file_stem,
    locate_media_file,
    match_sidecar_subtitles,
    media_directory_name,
    movie_file_stem,
    season_directory_name,
)
from media_manager.common.schemas import PublicMediaFile, SubtitleTrack
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


def test_match_sidecar_subtitles_finds_companions_excluding_video(tmp_path: Path):
    video = tmp_path / "Movie (2020).mkv"
    video.touch()
    (tmp_path / "Movie (2020).en.srt").touch()
    (tmp_path / "Movie (2020).eng.forced.ass").touch()
    (tmp_path / "Movie (2020).nfo").touch()
    (tmp_path / "Movie (2020) - 1080p.fre.srt").touch()  # different stem

    entries = [DirectoryEntry(p, None) for p in sorted(tmp_path.iterdir())]

    tracks = match_sidecar_subtitles(entries, stem="Movie (2020)", exclude=video)

    assert {(t.language, t.forced, t.codec) for t in tracks} == {
        ("en", False, "srt"),
        ("eng", True, "ass"),
    }
    assert all(t.source == "sidecar" for t in tracks)


def test_match_sidecar_subtitles_parses_hearing_impaired_and_bare_names(tmp_path: Path):
    (tmp_path / "Movie (2020).en.sdh.srt").touch()
    (tmp_path / "Movie (2020).srt").touch()

    entries = [DirectoryEntry(p, None) for p in sorted(tmp_path.iterdir())]
    tracks = match_sidecar_subtitles(entries, stem="Movie (2020)", exclude=None)

    sdh_track = next(t for t in tracks if t.language == "en")
    assert sdh_track.hearing_impaired is True

    bare_track = next(t for t in tracks if t.language is None)
    assert bare_track.forced is False
    assert bare_track.hearing_impaired is False


def test_match_sidecar_subtitles_does_not_misread_marker_token_as_language(
    tmp_path: Path,
):
    # "sdh"/"cc" also match the 2-3 letter language pattern - marker tokens
    # occurring before the real language token must not be picked up as it.
    (tmp_path / "Movie (2020).sdh.en.srt").touch()

    entries = [DirectoryEntry(p, None) for p in sorted(tmp_path.iterdir())]
    [track] = match_sidecar_subtitles(entries, stem="Movie (2020)", exclude=None)

    assert track.language == "en"
    assert track.hearing_impaired is True


def test_match_sidecar_subtitles_ignores_non_subtitle_extensions(tmp_path: Path):
    (tmp_path / "Movie (2020).jpg").touch()
    (tmp_path / "Movie (2020).txt").touch()

    entries = [DirectoryEntry(p, None) for p in sorted(tmp_path.iterdir())]
    assert match_sidecar_subtitles(entries, stem="Movie (2020)", exclude=None) == []


def test_attach_media_file_details_reports_sidecar_subtitles_for_stored_relative_path(
    tmp_path: Path,
):
    show_dir = tmp_path / "The Show (2005) [tmdbid-1]"
    season_dir = show_dir / "Season 1"
    season_dir.mkdir(parents=True)
    (season_dir / "The Show - S01E01.mkv").write_bytes(b"123")
    (season_dir / "The Show - S01E01.en.srt").touch()

    file = _public_file(relative_path="Season 1/The Show - S01E01.mkv")
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

    assert file.details is not None
    assert file.details.subtitles == [
        SubtitleTrack(language="en", source="sidecar", codec="srt")
    ]


def test_attach_media_file_details_finds_sidecars_for_a_hand_renamed_file(
    tmp_path: Path,
):
    # A stored `relative_path` can point at a file that doesn't follow this
    # app's naming scheme at all (hand-renamed, or written by another tool
    # like Bazarr) - sidecars must be matched against *that* file's own name,
    # not the canonical `location.stem`, which won't appear anywhere on disk.
    movie_dir = tmp_path / "The Movie (2024)"
    movie_dir.mkdir()
    (movie_dir / "Renamed Episode.mkv").write_bytes(b"123")
    (movie_dir / "Renamed Episode.en.srt").touch()

    file = _public_file(relative_path="Renamed Episode.mkv")
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

    assert file.details is not None
    assert file.details.subtitles == [
        SubtitleTrack(language="en", source="sidecar", codec="srt")
    ]


def test_attach_media_file_details_does_not_leak_subtitles_between_files(
    tmp_path: Path,
):
    # `probe.subtitles` may be the shared EMPTY_PROBE singleton; merging must
    # build a fresh list per file rather than mutating it, or one file's
    # sidecar subtitles would leak onto every other file sharing that probe.
    dir_a = tmp_path / "Movie A (2020)"
    dir_a.mkdir()
    (dir_a / "Movie A (2020).mkv").write_bytes(b"1")
    (dir_a / "Movie A (2020).en.srt").touch()

    dir_b = tmp_path / "Movie B (2021)"
    dir_b.mkdir()
    (dir_b / "Movie B (2021).mkv").write_bytes(b"1")

    file_a = _public_file()
    file_b = _public_file()
    asyncio.run(
        attach_media_file_details(
            [file_a, file_b],
            [
                MediaFileLocation(
                    directory=dir_a,
                    stem="Movie A (2020)",
                    relative_to=tmp_path,
                    media_root=dir_a,
                ),
                MediaFileLocation(
                    directory=dir_b,
                    stem="Movie B (2021)",
                    relative_to=tmp_path,
                    media_root=dir_b,
                ),
            ],
        )
    )

    assert len(file_a.details.subtitles) == 1
    assert file_b.details.subtitles == []

    # A second, independent call must not have accumulated state either.
    file_b_again = _public_file()
    asyncio.run(
        attach_media_file_details(
            [file_b_again],
            [
                MediaFileLocation(
                    directory=dir_b,
                    stem="Movie B (2021)",
                    relative_to=tmp_path,
                    media_root=dir_b,
                )
            ],
        )
    )
    assert file_b_again.details.subtitles == []
