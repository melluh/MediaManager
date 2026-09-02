"""
Shared on-disk file handling for media (movies and TV episodes alike).

The naming scheme used when importing a file is the same scheme used to find
it again afterwards, so both live here: importers build target paths with the
`*_file_stem` helpers, and the API resolves a stored file record back to a
real path with `locate_media_file`.
"""

import asyncio
import mimetypes
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from stat import S_ISREG

from media_manager.common.schemas import MediaFileDetails, PublicMediaFile
from media_manager.torrent.utils import remove_special_characters
from media_manager.torrent.video_probe import EMPTY_PROBE, probe_video_files


def movie_file_stem(
    movie_name: str, year: int | None, file_path_suffix: str = ""
) -> str:
    """Filename (without extension) a movie's file is imported as."""
    return _with_suffix(
        f"{remove_special_characters(movie_name)} ({year})", file_path_suffix
    )


def episode_file_stem(
    show_name: str,
    season_number: int,
    episode_number: int,
    file_path_suffix: str = "",
) -> str:
    """Filename (without extension) an episode's file is imported as."""
    return _with_suffix(
        f"{remove_special_characters(show_name)} - S{season_number:02d}E{episode_number:02d}",
        file_path_suffix,
    )


def media_directory_name(
    name: str, year: int | None, metadata_provider: str, external_id: int
) -> str:
    """
    Name of the directory a media item's files live in. Stored on the media
    row when it is added, so that a later metadata refresh renaming the media
    cannot orphan the files already on disk.
    """
    year_part = f" ({year})" if year is not None else ""
    return (
        f"{remove_special_characters(name)}{year_part}"
        f" [{metadata_provider}id-{external_id}]"
    )


def season_directory_name(season_number: int) -> str:
    """Name of the per-season subdirectory inside a show's root directory."""
    return f"Season {season_number}"


def _with_suffix(stem: str, file_path_suffix: str) -> str:
    return f"{stem} - {file_path_suffix}" if file_path_suffix else stem


@dataclass(frozen=True)
class MediaFileLocation:
    """Where a media file record is expected to live on disk."""

    directory: Path
    """Directory holding the file: a movie's root directory, or a show's season directory."""
    stem: str
    """Expected filename without extension, as produced by the `*_file_stem` helpers."""
    relative_to: Path
    """Directory reported paths are made relative to - the media type's library root."""
    media_root: Path
    """The media's own root directory, which a record's stored `relative_path` is relative to."""


def locate_media_file(location: MediaFileLocation) -> Path | None:
    """
    Finds the actual file for a location by scanning its directory for the
    expected stem, recovering whichever extension it was imported with.
    Prefers a video file when several extensions match (e.g. an accompanying
    subtitle track). Returns None when nothing matches - typically because
    the file hasn't been imported yet.
    """
    entry = match_stem(list_directory(location.directory), location.stem)
    return entry[0] if entry else None


@dataclass(frozen=True)
class DirectoryEntry:
    path: Path
    size_bytes: int | None


def list_directory(directory: Path) -> list[DirectoryEntry]:
    """
    One scandir per directory, carrying each entry's size along - so a whole
    season resolves from a single listing instead of a glob per episode.
    """
    entries: list[DirectoryEntry] = []
    try:
        with os.scandir(directory) as scan:
            for item in scan:
                if not item.is_file():
                    continue
                try:
                    size = item.stat().st_size
                except OSError:
                    size = None
                entries.append(DirectoryEntry(Path(item.path), size))
    except OSError:
        return []
    return sorted(entries, key=lambda entry: entry.path.name)


def match_stem(
    entries: list[DirectoryEntry], stem: str
) -> tuple[Path, int | None] | None:
    prefix = f"{stem}."
    candidates = [entry for entry in entries if entry.path.name.startswith(prefix)]
    video_candidates = [entry for entry in candidates if is_video_file(entry.path)]
    matched = next(iter(video_candidates or candidates), None)
    return (matched.path, matched.size_bytes) if matched else None


async def attach_media_file_details(
    files: Sequence[PublicMediaFile], locations: Sequence[MediaFileLocation]
) -> None:
    """
    Fills in `file_path`, `exists_on_disk` and `details` for each public media
    file from its location on disk, mutating them in place. A record that
    recorded its own `relative_path` when it was imported is resolved from
    that; the rest are found by matching their expected filename stem.

    Directory scanning and stat()ing happen in one worker thread for the whole
    batch, and the files that do exist are probed concurrently with a bounded
    number of ffprobe subprocesses (results are cached per file revision), so
    listing a full season stays a handful of syscalls rather than one blocking
    round-trip per episode.
    """
    if not files:
        return

    resolved_paths, sizes, expected_paths = await asyncio.to_thread(
        _resolve_batch, [file.relative_path for file in files], locations
    )

    # Only video files are worth an ffprobe; a record resolving to a stray
    # subtitle still reports its path and size.
    probe_targets = [
        (index, path)
        for index, path in enumerate(resolved_paths)
        if path is not None and is_video_file(path)
    ]
    probes = await probe_video_files(path for _, path in probe_targets)
    probe_by_index = {
        index: probe for (index, _), probe in zip(probe_targets, probes, strict=True)
    }

    for index, (file, location) in enumerate(zip(files, locations, strict=True)):
        resolved = resolved_paths[index]
        file.exists_on_disk = resolved is not None
        file.file_path = _relative_path(expected_paths[index], location.relative_to)
        if resolved is None:
            continue

        probe = probe_by_index.get(index, EMPTY_PROBE)
        file.details = MediaFileDetails(
            size_bytes=sizes[index],
            probed_quality=probe.quality,
            duration_seconds=probe.duration_seconds,
            width=probe.width,
            height=probe.height,
            video_codec=probe.video_codec,
            audio_codec=probe.audio_codec,
            audio_channels=probe.audio_channels,
            container=probe.container,
        )


def is_video_file(path: Path) -> bool:
    return (mimetypes.guess_type(path.name)[0] or "").startswith("video")


def _resolve_batch(
    relative_paths: Sequence[str | None],
    locations: Sequence[MediaFileLocation],
) -> tuple[list[Path | None], list[int | None], list[Path]]:
    listings: dict[Path, list[DirectoryEntry]] = {}
    resolved_paths: list[Path | None] = []
    sizes: list[int | None] = []
    expected_paths: list[Path] = []
    for relative_path, location in zip(relative_paths, locations, strict=True):
        if relative_path:
            # A record that knows where its file was written needs no listing.
            path = location.media_root / relative_path
            size = _file_size(path)
            expected_paths.append(path)
            resolved_paths.append(path if size is not None else None)
            sizes.append(size)
            continue
        if location.directory not in listings:
            listings[location.directory] = list_directory(location.directory)
        matched = match_stem(listings[location.directory], location.stem)
        expected_paths.append(
            matched[0] if matched else location.directory / location.stem
        )
        resolved_paths.append(matched[0] if matched else None)
        sizes.append(matched[1] if matched else None)
    return resolved_paths, sizes, expected_paths


def _file_size(path: Path) -> int | None:
    """Size of an existing regular file, or None when there is no file there."""
    try:
        stat = path.stat()
    except OSError:
        return None
    return stat.st_size if S_ISREG(stat.st_mode) else None


def _relative_path(path: Path, relative_to: Path) -> str:
    try:
        return str(path.relative_to(relative_to))
    except ValueError:
        # A library root that isn't a parent of the file (misconfigured, or
        # moved since import). Report the bare filename rather than the
        # absolute path - this value is served to API clients, which have no
        # business seeing the host's directory layout.
        return path.name
