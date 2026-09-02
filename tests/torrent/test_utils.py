from pathlib import Path

import pytest

from media_manager.torrent.utils import (
    classify_media_files,
    list_torrent_media_files,
    sanitize_torrent_title,
)


def test_classify_media_files_separates_video_and_subtitles():
    files = [
        Path("Movie (2024)/Movie.2024.1080p.mkv"),
        Path("Movie (2024)/Movie.2024.1080p.en.srt"),
        Path("Movie (2024)/sample.mp4"),
        Path("Movie (2024)/Movie.2024.1080p.nfo"),
    ]

    video_files, subtitle_files = classify_media_files(files)

    assert video_files == [
        Path("Movie (2024)/Movie.2024.1080p.mkv"),
        Path("Movie (2024)/sample.mp4"),
    ]
    assert subtitle_files == [Path("Movie (2024)/Movie.2024.1080p.en.srt")]


def test_classify_media_files_ignores_non_srt_text_files():
    files = [Path("readme.txt")]

    video_files, subtitle_files = classify_media_files(files)

    assert video_files == []
    assert subtitle_files == []


def test_list_torrent_media_files_does_not_extract_archives(tmp_path: Path):
    video_file = tmp_path / "movie.mkv"
    video_file.write_bytes(b"not a real video, just needs to exist")
    archive_file = tmp_path / "extras.zip"
    archive_file.write_bytes(b"PK\x03\x04not a real zip either")

    video_files, subtitle_files = list_torrent_media_files(directory=tmp_path)

    assert video_files == [video_file]
    assert subtitle_files == []
    # A real archive would fail to extract anyway; the point is this
    # function must not even attempt it (unlike get_files_for_import).
    assert archive_file.exists()


def test_list_torrent_media_files_requires_torrent_or_directory():
    with pytest.raises(ValueError, match="Either torrent or directory must be provided"):
        list_torrent_media_files()


def test_sanitize_torrent_title_leaves_normal_titles_untouched():
    title = "Movie.2024.1080p.WEB-DL.x264-GRP"
    assert sanitize_torrent_title(title) == title


@pytest.mark.parametrize(
    "malicious_title",
    [
        "../../../../etc/passwd",
        "..\\..\\..\\windows\\system32",
        "/etc/passwd",
        "....//....//etc",
    ],
)
def test_sanitize_torrent_title_neutralizes_path_traversal(malicious_title: str):
    sanitized = sanitize_torrent_title(malicious_title)

    assert "/" not in sanitized
    assert "\\" not in sanitized
    # Resolving it against a base directory must stay inside that directory.
    base = Path("/data/torrents")
    resolved = (base / sanitized).resolve()
    assert resolved.parent == base.resolve()
