import asyncio
import gzip
import io
import json
from pathlib import Path

import pytest

from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex import download
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.download import (
    FINAL_FILENAME,
    RawEntry,
    _merge_top_entries,
    _write_index_file,
    parse_export_stream,
    refresh_title_index,
)


def _gzip_ndjson(rows: list[dict]) -> bytes:
    lines = "\n".join(json.dumps(row) for row in rows)
    return gzip.compress(lines.encode("utf-8"))


def test_parse_export_stream_skips_adult_movies() -> None:
    rows = [
        {"id": 1, "original_title": "Clean Movie", "popularity": 10.0, "adult": False},
        {"id": 2, "original_title": "Adult Movie", "popularity": 5.0, "adult": True},
    ]
    stream = io.BytesIO(_gzip_ndjson(rows))

    entries = list(parse_export_stream(MediaType.movie, stream))

    assert [entry.id for entry in entries] == [1]


def test_parse_export_stream_tv_rows_have_no_adult_field() -> None:
    rows = [{"id": 1, "original_name": "Some Show", "popularity": 3.0}]
    stream = io.BytesIO(_gzip_ndjson(rows))

    entries = list(parse_export_stream(MediaType.tv, stream))

    assert len(entries) == 1
    assert entries[0].title == "Some Show"


def test_parse_export_stream_skips_malformed_and_incomplete_lines() -> None:
    raw = b'not json\n{"id": 1, "original_title": "Ok Movie", "popularity": 1.0}\n{"original_title": "No Id"}\n'
    stream = io.BytesIO(gzip.compress(raw))

    entries = list(parse_export_stream(MediaType.movie, stream))

    assert [entry.title for entry in entries] == ["Ok Movie"]


def test_merge_top_entries_bounds_by_popularity(tmp_path: Path) -> None:
    movie_rows = [
        {"id": i, "original_title": f"Movie {i}", "popularity": float(i), "adult": False}
        for i in range(10)
    ]
    tv_rows = [
        {"id": i, "original_name": f"Show {i}", "popularity": float(i) + 0.5}
        for i in range(10)
    ]
    movie_path = tmp_path / "movie.json.gz"
    tv_path = tmp_path / "tv.json.gz"
    movie_path.write_bytes(_gzip_ndjson(movie_rows))
    tv_path.write_bytes(_gzip_ndjson(tv_rows))

    entries = _merge_top_entries(
        {MediaType.movie: movie_path, MediaType.tv: tv_path}, max_entries=5
    )

    assert len(entries) == 5
    # Popularity descending.
    assert [entry.popularity for entry in entries] == sorted(
        (entry.popularity for entry in entries), reverse=True
    )
    # Only the 5 highest-popularity rows combined survive (9.5, 9, 8.5, 8, 7.5).
    assert entries[0].popularity == 9.5
    assert entries[-1].popularity == 7.5


def test_write_index_file_round_trips(tmp_path: Path) -> None:
    entries = [
        RawEntry(id=1, title="A", popularity=2.0, media_type=MediaType.movie),
        RawEntry(id=2, title="B", popularity=1.0, media_type=MediaType.tv),
    ]
    out_path = tmp_path / "index.ndjson.gz"

    _write_index_file(entries, out_path)

    with gzip.open(out_path, "rt", encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]

    assert rows == [
        {"id": 1, "t": "A", "p": 2.0, "m": "movie"},
        {"id": 2, "t": "B", "p": 1.0, "m": "tv"},
    ]


def test_refresh_leaves_existing_artifact_untouched_on_download_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    final_path = tmp_path / FINAL_FILENAME
    final_path.write_bytes(b"existing artifact contents")

    def _always_fails(_client, _media_type, _dest_path) -> None:
        msg = "simulated download failure"
        raise RuntimeError(msg)

    monkeypatch.setattr(download, "_fetch_export_file", _always_fails)

    asyncio.run(refresh_title_index(tmp_path, TitleIndexConfig()))

    assert final_path.read_bytes() == b"existing artifact contents"
    assert not (tmp_path / f"{FINAL_FILENAME}.tmp").exists()
