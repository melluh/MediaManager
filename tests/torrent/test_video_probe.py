from pathlib import Path

from media_manager.torrent.schemas import Quality
from media_manager.torrent.video_probe import probe_video_file, resolve_file_quality


def test_probe_video_file_returns_none_for_missing_file(tmp_path: Path):
    # No ffprobe binary is guaranteed in test environments, and even if
    # present it can't probe a file that doesn't exist - either way this
    # must degrade to (None, None) rather than raise.
    quality, duration = probe_video_file(tmp_path / "does-not-exist.mkv")

    assert quality is None
    assert duration is None


def test_resolve_file_quality_prefers_probed_quality():
    assert (
        resolve_file_quality(Quality.uhd, "movie.unknown.mkv", Quality.sd)
        == Quality.uhd
    )


def test_resolve_file_quality_falls_back_to_filename():
    assert (
        resolve_file_quality(None, "Movie.2024.1080p.WEB-DL.mkv", Quality.sd)
        == Quality.fullhd
    )


def test_resolve_file_quality_falls_back_to_torrent_quality():
    assert (
        resolve_file_quality(None, "movie.mkv", Quality.hd) == Quality.hd
    )
