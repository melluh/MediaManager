import asyncio
import gzip
import heapq
import itertools
import json
import logging
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import IO

import httpx

from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex.config import TitleIndexConfig

log = logging.getLogger(__name__)

EXPORT_BASE_URL = "http://files.tmdb.org/p/exports"
FINAL_FILENAME = "title_index.ndjson.gz"

_EXPORT_KIND: dict[MediaType, str] = {
    MediaType.movie: "movie_ids",
    MediaType.tv: "tv_series_ids",
}
_TITLE_FIELD: dict[MediaType, str] = {
    MediaType.movie: "original_title",
    MediaType.tv: "original_name",
}


@dataclass(frozen=True, slots=True)
class RawEntry:
    id: int
    title: str
    popularity: float
    media_type: MediaType


def parse_export_stream(media_type: MediaType, gzip_stream: IO[bytes]) -> Iterator[RawEntry]:
    """
    Parses one daily-export NDJSON stream (still gzip-compressed) into
    `RawEntry` rows, skipping adult movies (the "adult" field only exists on
    the movie export - never checked for TV rows) and any line that fails to
    parse or is missing the fields we need.
    """
    title_field = _TITLE_FIELD[media_type]
    with gzip.GzipFile(fileobj=gzip_stream) as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            if media_type is MediaType.movie and row.get("adult"):
                continue

            entry_id = row.get("id")
            title = row.get(title_field)
            if entry_id is None or not title:
                continue

            yield RawEntry(
                id=int(entry_id),
                title=title,
                popularity=float(row.get("popularity") or 0.0),
                media_type=media_type,
            )


def _merge_top_entries(
    raw_paths: dict[MediaType, Path], max_entries: int
) -> list[RawEntry]:
    """
    Streams every raw export file and keeps only the `max_entries` highest-
    popularity rows combined, via a bounded min-heap (O(n log k), memory
    bounded by `max_entries` regardless of how large the raw exports are).

    Returns entries sorted by popularity descending.
    """
    heap: list[tuple[float, int, RawEntry]] = []
    tie_breaker = itertools.count()
    for media_type, path in raw_paths.items():
        with path.open("rb") as fh:
            for entry in parse_export_stream(media_type, fh):
                item = (entry.popularity, next(tie_breaker), entry)
                if len(heap) < max_entries:
                    heapq.heappush(heap, item)
                elif item[0] > heap[0][0]:
                    heapq.heapreplace(heap, item)
    heap.sort(key=lambda item: item[0], reverse=True)
    return [item[2] for item in heap]


def _write_index_file(entries: list[RawEntry], tmp_path: Path) -> None:
    with gzip.open(tmp_path, "wt", encoding="utf-8") as fh:
        for entry in entries:
            fh.write(
                json.dumps(
                    {
                        "id": entry.id,
                        "t": entry.title,
                        "p": entry.popularity,
                        "m": entry.media_type.value,
                    }
                )
                + "\n"
            )


def _fetch_export_file(
    client: httpx.Client, media_type: MediaType, dest_path: Path
) -> None:
    """
    Downloads today's daily export for `media_type` directly from
    files.tmdb.org (a static, unauthenticated file - no need to go through
    the metadata_relay service, which exists only to hold a TMDB API key).
    Falls back to yesterday's date once, since TMDB's publish time can slip.

    Blocking (sync httpx client + plain file IO) by design - see
    `_refresh_title_index_sync`, which this is only ever called from inside
    an `asyncio.to_thread` worker.
    """
    kind = _EXPORT_KIND[media_type]
    today = datetime.now(UTC).date()
    for day_offset in (0, 1):
        date = today - timedelta(days=day_offset)
        url = f"{EXPORT_BASE_URL}/{kind}_{date:%m_%d_%Y}.json.gz"
        with client.stream("GET", url, timeout=120) as response:
            if response.status_code == HTTPStatus.NOT_FOUND:
                continue
            response.raise_for_status()
            with dest_path.open("wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)
            return
    msg = f"TMDB daily export for {kind} not found (tried today and yesterday)"
    raise RuntimeError(msg)


def _refresh_title_index_sync(directory: Path, settings: TitleIndexConfig) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    final_path = directory / FINAL_FILENAME
    tmp_final_path = directory / f"{FINAL_FILENAME}.tmp"

    with tempfile.TemporaryDirectory(dir=directory) as scratch_dir:
        raw_paths = {
            media_type: Path(scratch_dir) / f"{kind}.json.gz"
            for media_type, kind in _EXPORT_KIND.items()
        }

        try:
            with httpx.Client() as client:
                for media_type, dest_path in raw_paths.items():
                    _fetch_export_file(client, media_type, dest_path)
        except (httpx.HTTPError, RuntimeError):
            log.exception(
                "Failed to download TMDB daily export; keeping existing title index"
            )
            return

        try:
            entries = _merge_top_entries(raw_paths, settings.max_entries)
            _write_index_file(entries, tmp_final_path)
        except Exception:
            log.exception("Failed to build TMDB title index; keeping existing index")
            tmp_final_path.unlink(missing_ok=True)
            return

    tmp_final_path.replace(final_path)
    log.info(
        "Refreshed TMDB title index: %d entries (lowest popularity kept: %.3f)",
        len(entries),
        entries[-1].popularity if entries else 0.0,
    )


async def refresh_title_index(directory: Path, settings: TitleIndexConfig) -> None:
    """
    Downloads the latest TMDB daily ID exports, compacts them into a small
    popularity-ranked artifact, and atomically swaps it into place. On any
    failure, the previous artifact (if any) is left untouched rather than
    ending up with a partial or empty index.

    All the actual (blocking) work happens in `_refresh_title_index_sync`,
    run off the event loop.
    """
    await asyncio.to_thread(_refresh_title_index_sync, directory, settings)


def is_stale(directory: Path, stale_after_hours: float) -> bool:
    final_path = directory / FINAL_FILENAME
    try:
        mtime = final_path.stat().st_mtime
    except FileNotFoundError:
        return True
    return (time.time() - mtime) > stale_after_hours * 3600
