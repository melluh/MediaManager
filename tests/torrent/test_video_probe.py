from pathlib import Path

from media_manager.common.languages import UNKNOWN_LANGUAGE
from media_manager.common.schemas import SubtitleLanguage, SubtitleTrack
from media_manager.torrent.schemas import Quality
from media_manager.torrent.video_probe import (
    EMPTY_PROBE,
    _sanitize_tag,
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
    assert _to_probe({}).subtitles == []


def test_to_probe_reads_all_subtitle_streams_with_language_and_disposition():
    probe = _to_probe(
        {
            "streams": [
                {
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "eng"},
                    "disposition": {"forced": 1, "hearing_impaired": 0},
                },
                {
                    "codec_type": "subtitle",
                    "codec_name": "ass",
                    "tags": {"language": "fre"},
                    "disposition": {"forced": 0, "hearing_impaired": 1},
                },
            ]
        }
    )

    assert probe.subtitles == [
        SubtitleTrack(
            language=SubtitleLanguage(code="eng", name="English"),
            source="embedded",
            forced=True,
            hearing_impaired=False,
            codec="subrip",
        ),
        SubtitleTrack(
            language=SubtitleLanguage(code="fra", name="French"),
            source="embedded",
            forced=False,
            hearing_impaired=True,
            codec="ass",
        ),
    ]


def test_to_probe_reports_untagged_and_undetermined_subtitles_as_unknown():
    probe = _to_probe(
        {
            "streams": [
                {"codec_type": "subtitle", "codec_name": "subrip"},
                {
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "und"},
                },
                {
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "<script>"},
                },
            ]
        }
    )

    assert [track.language for track in probe.subtitles] == [UNKNOWN_LANGUAGE] * 3


def test_sanitize_tag_rejects_hostile_language_values():
    # Container metadata comes from the file itself (an untrusted download),
    # so it must never be trusted as a plain string: oversized values are
    # truncated, control characters and non-string JSON types are rejected
    # outright rather than passed through.
    assert _sanitize_tag("eng") == "eng"
    assert _sanitize_tag("a" * 100) == "a" * 32
    assert _sanitize_tag("en\x00g\x1b") == "eng"
    # Not HTML-escaped here - sanitization only bounds length/control chars;
    # safety against injection is enforced by never using {@html} on the
    # frontend and by Svelte's default escaping of plain interpolation.
    assert _sanitize_tag("<script>alert(1)</script>") == "<script>alert(1)</script>"
    assert _sanitize_tag("   ") is None
    assert _sanitize_tag(None) is None
    assert _sanitize_tag(12345) is None
    assert _sanitize_tag({"nested": "dict"}) is None


def test_probe_video_file_caches_per_file_revision(tmp_path: Path, monkeypatch):
    file = tmp_path / "movie.mkv"
    file.write_bytes(b"data")

    calls = []

    def _fake_run(path: Path):
        calls.append(path)
        return EMPTY_PROBE

    monkeypatch.setattr("media_manager.torrent.video_probe._run_ffprobe", _fake_run)

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
    assert resolve_file_quality(None, "movie.mkv", Quality.hd) == Quality.hd
