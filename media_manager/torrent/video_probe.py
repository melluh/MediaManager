import asyncio
import json
import logging
import shutil
import subprocess
import threading
import weakref
from collections import OrderedDict
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel

from media_manager.indexer.title_parsing import derive_quality
from media_manager.torrent.schemas import Quality

log = logging.getLogger(__name__)

_FFPROBE_TIMEOUT_SECONDS = 15

# ffprobe spawns a subprocess per file; a media library (or a single torrent)
# can hold an arbitrary number of video files, so probing is always bounded.
MAX_CONCURRENT_PROBES = 4
# Kept per event loop: an asyncio.Semaphore binds to the loop it is first
# awaited on, and would raise RuntimeError if reused from another one.
_probe_semaphores: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, asyncio.Semaphore
] = weakref.WeakKeyDictionary()

# Probing the same unchanged file over and over (every /files request, for
# every episode of a season) is pure waste, so results are memoized against
# the file's identity on disk. Probing runs in worker threads, so the cache
# needs a lock - the read-then-reorder and the eviction are not atomic on
# their own.
_PROBE_CACHE_MAX_ENTRIES = 4096
_probe_cache: OrderedDict[tuple[str, int, int], "VideoProbe"] = OrderedDict()
_probe_cache_lock = threading.Lock()


class VideoProbe(BaseModel):
    """
    What ffprobe could tell us about a video file. Every field is optional:
    probing is advisory, and an unavailable ffprobe or an unreadable file
    yields an empty result rather than an error.
    """

    quality: Quality | None = None
    """Quality derived from the video stream's height."""
    duration_seconds: int | None = None
    width: int | None = None
    height: int | None = None
    video_codec: str | None = None
    audio_codec: str | None = None
    audio_channels: int | None = None
    container: str | None = None


EMPTY_PROBE = VideoProbe()


def probe_video_file(path: Path) -> VideoProbe:
    """
    Best-effort ffprobe of a video file's streams and duration.

    Returns an empty `VideoProbe` if ffprobe is unavailable or the file can't
    be probed; individual fields are None when missing from ffprobe's output.
    Never raises - probing is advisory, not required for import.

    Results are cached per (path, size, mtime), so re-probing an unchanged
    file is free.
    """
    cache_key = _cache_key(path)
    if cache_key is None:
        return EMPTY_PROBE

    with _probe_cache_lock:
        cached = _probe_cache.get(cache_key)
        if cached is not None:
            _probe_cache.move_to_end(cache_key)
            return cached

    probe = _run_ffprobe(path)
    _store_in_cache(cache_key, probe)
    return probe


async def probe_video_files(paths: Iterable[Path]) -> list[VideoProbe]:
    """
    Probes several files concurrently, off the event loop and with a bounded
    number of ffprobe subprocesses in flight.
    """

    semaphore = _semaphore_for_running_loop()

    async def _probe(path: Path) -> VideoProbe:
        async with semaphore:
            return await asyncio.to_thread(probe_video_file, path)

    return list(await asyncio.gather(*(_probe(path) for path in paths)))


def _semaphore_for_running_loop() -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    semaphore = _probe_semaphores.get(loop)
    if semaphore is None:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_PROBES)
        _probe_semaphores[loop] = semaphore
    return semaphore


def _cache_key(path: Path) -> tuple[str, int, int] | None:
    try:
        stat = path.stat()
    except OSError:
        return None
    return str(path), stat.st_size, stat.st_mtime_ns


def _store_in_cache(key: tuple[str, int, int], probe: VideoProbe) -> None:
    with _probe_cache_lock:
        _probe_cache[key] = probe
        _probe_cache.move_to_end(key)
        while len(_probe_cache) > _PROBE_CACHE_MAX_ENTRIES:
            _probe_cache.popitem(last=False)


def _run_ffprobe(path: Path) -> VideoProbe:
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        log.debug("ffprobe is not installed, skipping video probe")
        return EMPTY_PROBE

    try:
        result = subprocess.run(  # noqa: S603 - argv is fully constructed by us
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "stream=codec_type,codec_name,width,height,channels:format=duration,format_name",
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
        return EMPTY_PROBE

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        log.debug(f"ffprobe returned unparseable output for {path}")
        return EMPTY_PROBE

    return _to_probe(data)


def _to_probe(probe_data: dict) -> VideoProbe:
    streams = probe_data.get("streams") or []
    video_stream = _first_stream_of_type(streams, "video")
    audio_stream = _first_stream_of_type(streams, "audio")

    height = _as_int(video_stream.get("height"))
    return VideoProbe(
        quality=_height_to_quality(height) if height is not None else None,
        duration_seconds=_extract_duration_seconds(probe_data),
        width=_as_int(video_stream.get("width")),
        height=height,
        video_codec=_as_str(video_stream.get("codec_name")),
        audio_codec=_as_str(audio_stream.get("codec_name")),
        audio_channels=_as_int(audio_stream.get("channels")),
        container=_extract_container(probe_data),
    )


def _first_stream_of_type(streams: list, codec_type: str) -> dict:
    return next(
        (
            stream
            for stream in streams
            if isinstance(stream, dict) and stream.get("codec_type") == codec_type
        ),
        {},
    )


def _as_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _as_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def _extract_container(probe_data: dict) -> str | None:
    # ffprobe reports a comma-separated list of formats the file matches
    # (e.g. "mov,mp4,m4a,3gp,3g2,mj2"); the first is the most specific.
    format_name = _as_str(probe_data.get("format", {}).get("format_name"))
    return format_name.split(",")[0] if format_name else None


def _extract_duration_seconds(probe_data: dict) -> int | None:
    raw_duration = probe_data.get("format", {}).get("duration")
    if raw_duration is None:
        return None
    try:
        return int(float(raw_duration))
    except (TypeError, ValueError):
        return None


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
