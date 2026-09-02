from pathlib import Path

from media_manager.torrent.schemas import Quality
from media_manager.torrent.video_probe import (
    EMPTY_PROBE,
    _to_probe,
    probe_video_file,
    resolve_file_quality,
)


def test_probe_video_file_returns_empty_for_missing_file(tmp_path: Path):
    # No ffprobe binary is guaranteed in test environments, and even if
    # present it can't probe a file that doesn't exist - either way this
    # must degrade to an empty probe rather than raise.
    assert probe_video_file(tmp_path / "does-not-exist.mkv") == EMPTY_PROBE


def test_to_probe_reads_video_audio_and_format():
    probe = _to_probe(
        {
            "streams": [
                {"codec_type": "audio", "codec_name": "eac3", "channels": 6},
                {
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "width": 3840,
                    "height": 2160,
                },
            ],
            "format": {"duration": "7261.5", "format_name": "matroska,webm"},
        }
    )

    assert probe.quality == Quality.uhd
    assert probe.width == 3840
    assert probe.height == 2160
    assert probe.video_codec == "hevc"
    assert probe.audio_codec == "eac3"
    assert probe.audio_channels == 6
    assert probe.duration_seconds == 7261
    assert probe.container == "matroska"


def test_to_probe_tolerates_missing_streams_and_format():
    assert _to_probe({}) == EMPTY_PROBE


def test_probe_video_file_caches_per_file_revision(tmp_path: Path, monkeypatch):
    file = tmp_path / "movie.mkv"
    file.write_bytes(b"data")

    calls = []

    def _fake_run(path: Path):
        calls.append(path)
        return EMPTY_PROBE

    monkeypatch.setattr(
        "media_manager.torrent.video_probe._run_ffprobe", _fake_run
    )

    probe_video_file(file)
    probe_video_file(file)
    assert len(calls) == 1

    # A changed file must not keep serving the stale probe.
    file.write_bytes(b"different data")
    probe_video_file(file)
    assert len(calls) == 2


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
