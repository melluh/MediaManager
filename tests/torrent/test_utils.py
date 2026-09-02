from pathlib import Path
from types import SimpleNamespace

import pytest

from media_manager.torrent.utils import (
    classify_media_files,
    get_importable_media_directories,
    import_file,
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


@pytest.fixture
def patch_libraries(monkeypatch):
    """Patches the configured libraries `get_importable_media_directories` excludes."""

    def _patch(library_paths: list[Path]):
        libraries = [SimpleNamespace(path=str(p)) for p in library_paths]

        class _FakeMediaManagerConfig:
            misc = SimpleNamespace(movie_libraries=libraries, tv_libraries=[])

        monkeypatch.setattr(
            "media_manager.torrent.utils.MediaManagerConfig",
            lambda: _FakeMediaManagerConfig(),
        )

    return _patch


def test_get_importable_media_directories_excludes_claimed_directories(
    tmp_path: Path, patch_libraries
):
    patch_libraries([])
    claimed = tmp_path / "Beautiful Boy (2018) [tmdbid-451915]"
    claimed.mkdir()
    unclaimed = tmp_path / "Oppenheimer (2023)"
    unclaimed.mkdir()

    directories = get_importable_media_directories(
        tmp_path, claimed_directory_names={claimed.name}
    )

    assert directories == [unclaimed]


def test_get_importable_media_directories_without_claimed_set_offers_everything(
    tmp_path: Path, patch_libraries
):
    patch_libraries([])
    first = tmp_path / "Beautiful Boy (2018) [tmdbid-451915]"
    first.mkdir()
    second = tmp_path / "Oppenheimer (2023)"
    second.mkdir()

    directories = get_importable_media_directories(tmp_path)

    assert sorted(directories) == [first, second]


def test_get_importable_media_directories_excludes_dotted_and_library_roots(
    tmp_path: Path, patch_libraries
):
    library_root = tmp_path / "my-custom-library"
    library_root.mkdir()
    patch_libraries([library_root])
    hidden = tmp_path / ".Ignored Show"
    hidden.mkdir()
    importable = tmp_path / "Rick and Morty"
    importable.mkdir()
    (tmp_path / "loose-file.mkv").write_bytes(b"")

    directories = get_importable_media_directories(
        tmp_path, claimed_directory_names=set()
    )

    assert directories == [importable]


def test_import_file_leaves_an_already_placed_file_alone(tmp_path: Path):
    # A library directory offered for import again imports into itself, so the
    # target and the source can be the very same file. Unlinking it first
    # would destroy the only copy the user has.
    movie_file = tmp_path / "Beautiful Boy (2018) - IMPORTED.mkv"
    movie_file.write_bytes(b"the only copy")

    import_file(target_file=movie_file, source_file=movie_file)

    assert movie_file.exists()
    assert movie_file.read_bytes() == b"the only copy"


def test_import_file_leaves_an_existing_hardlink_alone(tmp_path: Path):
    source = tmp_path / "source.mkv"
    source.write_bytes(b"payload")
    target = tmp_path / "Movie (2024).mkv"
    target.hardlink_to(source)
    target_inode = target.stat().st_ino

    import_file(target_file=target, source_file=source)

    assert target.stat().st_ino == target_inode
    assert target.read_bytes() == b"payload"


def test_import_file_replaces_a_different_file_at_the_target(tmp_path: Path):
    source = tmp_path / "source.mkv"
    source.write_bytes(b"new payload")
    target = tmp_path / "Movie (2024).mkv"
    target.write_bytes(b"stale payload")

    import_file(target_file=target, source_file=source)

    assert target.read_bytes() == b"new payload"
    assert target.samefile(source)
