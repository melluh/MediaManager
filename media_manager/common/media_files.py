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

from media_manager.common.languages import language_or_unknown, parse_language
from media_manager.common.schemas import (
    MediaFileDetails,
    PublicMediaFile,
    SubtitleLanguage,
    SubtitleTrack,
)
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


SUBTITLE_EXTENSIONS = {".srt", ".ass", ".ssa", ".vtt", ".sub"}


def is_subtitle_file(path: Path) -> bool:
    # Extension-based, not mimetypes.guess_type: .ass/.ssa/.vtt don't
    # reliably map to a text/* mimetype, which is exactly what limits
    # torrent/utils.py:classify_media_files to recognizing only .srt today.
    return path.suffix.lower() in SUBTITLE_EXTENSIONS


def match_sidecar_subtitles(
    entries: list[DirectoryEntry], stem: str, exclude: Path | None
) -> list[SubtitleTrack]:
    """
    Sidecar subtitle files matching the same filename stem as a media file
    (e.g. "Movie (2020).en.srt" next to "Movie (2020).mkv"), excluding
    whichever entry was already resolved as the main file.
    """
    prefix = f"{stem}."
    return [
        _parse_sidecar_subtitle(entry, stem)
        for entry in entries
        if entry.path.name.startswith(prefix)
        and entry.path != exclude
        and is_subtitle_file(entry.path)
    ]


# Tokens parsed out of a sidecar filename are untrusted text (the filename
# comes from a downloaded file, not the user) - only a token `parse_language`
# recognizes is kept; anything else is dropped rather than passed through.
_HEARING_IMPAIRED_TOKENS = {"sdh", "hi", "cc"}


def _parse_sidecar_subtitle(entry: DirectoryEntry, stem: str) -> SubtitleTrack:
    name_without_extension = entry.path.stem
    remainder = name_without_extension[len(stem) :].strip(".")
    words = [word for word in remainder.split(".") if word]
    lowered = [word.lower() for word in words]

    forced = "forced" in lowered
    hearing_impaired = any(word in _HEARING_IMPAIRED_TOKENS for word in lowered)
    # Marker words are excluded from language candidacy: "hi" is also the ISO
    # 639-1 code for Hindi, and ".sdh.en.srt" must not be read as anything
    # but English. The marker meaning wins.
    language = next(
        (
            parsed
            for word in words
            if word.lower() != "forced"
            and word.lower() not in _HEARING_IMPAIRED_TOKENS
            and (parsed := parse_language(word)) is not None
        ),
        None,
    ) or language_or_unknown(None)

    return SubtitleTrack(
        language=language,
        source="sidecar",
        forced=forced,
        hearing_impaired=hearing_impaired,
        codec=entry.path.suffix.lower().removeprefix("."),
    )


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

    resolved_paths, sizes, expected_paths, sidecar_subtitles = await asyncio.to_thread(
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
        # A fresh list, never probe.subtitles directly: `probe` may be the
        # shared EMPTY_PROBE singleton or a cached VideoProbe, and appending
        # this file's sidecar subtitles to it in place would corrupt the
        # ffprobe cache or leak them onto every other unprobed file.
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
            subtitles=[*probe.subtitles, *sidecar_subtitles[index]],
        )


def distinct_subtitle_languages(
    files: Sequence[PublicMediaFile],
) -> list[SubtitleLanguage] | None:
    """
    Every distinct subtitle language across a set of files already passed
    through `attach_media_file_details`, sorted by name. None when none of
    the files exist on disk, which is distinct from existing files that
    simply have no subtitles (an empty list).
    """
    on_disk = [
        file.details
        for file in files
        if file.exists_on_disk and file.details is not None
    ]
    if not on_disk:
        return None
    languages = {
        (track.language.code, track.language.region): track.language
        for details in on_disk
        for track in details.subtitles
    }
    return sorted(languages.values(), key=lambda language: language.name)


def is_video_file(path: Path) -> bool:
    return (mimetypes.guess_type(path.name)[0] or "").startswith("video")


def _resolve_batch(
    relative_paths: Sequence[str | None],
    locations: Sequence[MediaFileLocation],
) -> tuple[list[Path | None], list[int | None], list[Path], list[list[SubtitleTrack]]]:
    listings: dict[Path, list[DirectoryEntry]] = {}
    resolved_paths: list[Path | None] = []
    sizes: list[int | None] = []
    expected_paths: list[Path] = []
    sidecar_subtitles: list[list[SubtitleTrack]] = []
    for relative_path, location in zip(relative_paths, locations, strict=True):
        if relative_path:
            # A record that knows where its file was written needs no listing
            # to find *itself* - but sidecar subtitles still need one, so
            # this reuses the same per-directory `listings` cache the
            # stem-matching branch below relies on.
            path = location.media_root / relative_path
            size = _file_size(path)
            expected_paths.append(path)
            resolved_paths.append(path if size is not None else None)
            sizes.append(size)
            if size is None:
                sidecar_subtitles.append([])
                continue
            directory = path.parent
            if directory not in listings:
                listings[directory] = list_directory(directory)
            # Matched against the resolved file's own stem, not
            # `location.stem`: a `relative_path` can point at a hand-renamed
            # file (or one written by another tool) that doesn't follow this
            # app's naming scheme at all, and sidecars sitting next to it
            # follow *its* name, not the canonical one.
            sidecar_subtitles.append(
                match_sidecar_subtitles(listings[directory], path.stem, exclude=path)
            )
            continue
        if location.directory not in listings:
            listings[location.directory] = list_directory(location.directory)
        matched = match_stem(listings[location.directory], location.stem)
        expected_paths.append(
            matched[0] if matched else location.directory / location.stem
        )
        resolved_paths.append(matched[0] if matched else None)
        sizes.append(matched[1] if matched else None)
        sidecar_subtitles.append(
            match_sidecar_subtitles(
                listings[location.directory],
                location.stem,
                exclude=matched[0] if matched else None,
            )
        )
    return resolved_paths, sizes, expected_paths, sidecar_subtitles


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
