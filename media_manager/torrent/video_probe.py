import json
import logging
import shutil
import subprocess
from pathlib import Path

from media_manager.indexer.title_parsing import derive_quality
from media_manager.torrent.schemas import Quality

log = logging.getLogger(__name__)

_FFPROBE_TIMEOUT_SECONDS = 15


def probe_video_file(path: Path) -> tuple[Quality | None, int | None]:
    """
    Best-effort ffprobe of a video file's resolution and duration.

    Returns (quality, duration_seconds); either may be None if ffprobe is
    unavailable, the file can't be probed, or a value is missing from its
    output. Never raises - probing is advisory, not required for import.
    """
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        log.debug("ffprobe is not installed, skipping video probe")
        return None, None

    try:
        result = subprocess.run(  # noqa: S603 - argv is fully constructed by us
            [
                ffprobe_path,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=height:format=duration",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=_FFPROBE_TIMEOUT_SECONDS,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        log.debug(f"ffprobe failed for {path}", exc_info=True)
        return None, None

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        log.debug(f"ffprobe returned unparseable output for {path}")
        return None, None

    return _extract_quality(data), _extract_duration_seconds(data)


def _extract_duration_seconds(probe_data: dict) -> int | None:
    raw_duration = probe_data.get("format", {}).get("duration")
    if raw_duration is None:
        return None
    try:
        return int(float(raw_duration))
    except (TypeError, ValueError):
        return None


def _extract_quality(probe_data: dict) -> Quality | None:
    streams = probe_data.get("streams") or []
    if not streams:
        return None
    height = streams[0].get("height")
    if not isinstance(height, int):
        return None
    return _height_to_quality(height)


def _height_to_quality(height: int) -> Quality:
    if height >= 2000:
        return Quality.uhd
    if height >= 1000:
        return Quality.fullhd
    if height >= 700:
        return Quality.hd
    return Quality.sd


def resolve_file_quality(
    probed_quality: Quality | None, file_name: str, fallback_quality: Quality
) -> Quality:
    """
    Best available quality for a video file: ffprobe's measured resolution,
    falling back to guessing from the filename, falling back to the
    torrent's own recorded quality.
    """
    if probed_quality is not None:
        return probed_quality
    quality_from_filename = derive_quality(file_name)
    if quality_from_filename != Quality.unknown:
        return quality_from_filename
    return fallback_quality
