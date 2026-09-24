"""
Shared on-disk file handling for media (movies and TV episodes alike).

Importers build target paths with the `*_file_stem` helpers, and every file
record stores the `relative_path` it was written to. What probing a file
finds is stored on its record too, and only re-probed once the file changes
(see `refresh_media_file_details`).
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
    Quality,
    SubtitleLanguage,
    SubtitleTrack,
)
from media_manager.torrent.utils import remove_special_characters
from media_manager.torrent.video_probe import probe_video_files


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
    """Where the paths of a media item's file records are resolved from."""

    relative_to: Path
    """Directory reported paths are made relative to - the media type's library root."""
    media_root: Path
    """The media's own root directory, which a record's stored `relative_path` is relative to."""


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


async def refresh_media_file_details[F: PublicMediaFile](
    files: Sequence[F], locations: Sequence[MediaFileLocation]
) -> list[F]:
    """
    Fills in `file_path` and `exists_on_disk` for each file record from the
    disk, and brings its stored `details` up to date, mutating the files in
    place. Returns the files whose `details` changed, for the caller to store.

    ffprobe only runs for a video file never probed before, or one whose
    size or mtime changed since it was - every other file reuses its stored
    probe, so this is a stat and a directory listing per file. Sidecar
    subtitles are re-read every time (they can change without the video
    changing, and cost no ffprobe). A file that's gone keeps its last stored
    details; `exists_on_disk` says it's missing.

    Stat()ing and directory listing happen in one worker thread for the
    whole batch, and stale files are probed concurrently with a bounded
    number of ffprobe subprocesses.
    """
    if not files:
        return []

    states = await asyncio.to_thread(
        _stat_batch, [file.relative_path for file in files], locations
    )

    # Only video files are worth an ffprobe; a record resolving to a stray
    # subtitle still reports its path, size and sidecars.
    probe_indices = [
        index
        for index, (file, state) in enumerate(zip(files, states, strict=True))
        if state.exists and is_video_file(state.path) and _probe_is_stale(file, state)
    ]
    probes = await probe_video_files(states[index].path for index in probe_indices)
    probe_by_index = dict(zip(probe_indices, probes, strict=True))

    changed: list[F] = []
    for index, (file, location, state) in enumerate(
        zip(files, locations, states, strict=True)
    ):
        file.file_path = _relative_path(state.path, location.relative_to)
        file.exists_on_disk = state.exists
        if not state.exists:
            continue

        probe = probe_by_index.get(index)
        if probe is not None:
            base = MediaFileDetails(
                quality=probe.quality,
                duration_seconds=probe.duration_seconds,
                width=probe.width,
                height=probe.height,
                video_codec=probe.video_codec,
                audio_codec=probe.audio_codec,
                audio_channels=probe.audio_channels,
                container=probe.container,
                subtitles=probe.subtitles,
            )
        elif file.details is not None and not _probe_is_stale(file, state):
            base = file.details
        else:
            base = MediaFileDetails()
        embedded = [track for track in base.subtitles if track.source == "embedded"]
        # A fresh list, never base.subtitles extended in place: `base` may be
        # built from a cached VideoProbe, and appending this file's sidecars
        # to it would corrupt the ffprobe cache.
        details = base.model_copy(
            update={
                "size_bytes": state.size_bytes,
                "subtitles": [*embedded, *state.sidecar_subtitles],
            }
        )
        if details != file.details or file.probed_mtime_ns != state.mtime_ns:
            file.details = details
            file.probed_mtime_ns = state.mtime_ns
            changed.append(file)
    return changed


def distinct_subtitle_languages(
    details: Sequence[MediaFileDetails | None],
) -> list[SubtitleLanguage] | None:
    """
    Every distinct subtitle language across a media item's files' probe
    details, sorted by name. None when none of the files has been probed,
    which is distinct from probed files that simply have no subtitles (an
    empty list).
    """
    probed = [file_details for file_details in details if file_details is not None]
    if not probed:
        return None
    languages = {
        (track.language.code, track.language.region): track.language
        for file_details in probed
        for track in file_details.subtitles
    }
    return sorted(languages.values(), key=lambda language: language.name)


def best_quality(details: Sequence[MediaFileDetails | None]) -> Quality | None:
    """The best probed quality across a media item's files, if any has one."""
    return min(
        (
            file_details.quality
            for file_details in details
            if file_details is not None and file_details.quality is not None
        ),
        key=lambda quality: quality.value,
        default=None,
    )


def is_video_file(path: Path) -> bool:
    return (mimetypes.guess_type(path.name)[0] or "").startswith("video")


@dataclass(frozen=True)
class _FileState:
    path: Path
    size_bytes: int | None
    """None when there is no file at `path`."""
    mtime_ns: int | None
    sidecar_subtitles: list[SubtitleTrack]

    @property
    def exists(self) -> bool:
        return self.size_bytes is not None


def _probe_is_stale(file: PublicMediaFile, state: _FileState) -> bool:
    return (
        file.details is None
        or file.probed_mtime_ns != state.mtime_ns
        or file.details.size_bytes != state.size_bytes
    )


def _stat_batch(
    relative_paths: Sequence[str],
    locations: Sequence[MediaFileLocation],
) -> list[_FileState]:
    listings: dict[Path, list[DirectoryEntry]] = {}
    states: list[_FileState] = []
    for relative_path, location in zip(relative_paths, locations, strict=True):
        path = location.media_root / relative_path
        try:
            stat = path.stat()
        except OSError:
            stat = None
        if stat is None or not S_ISREG(stat.st_mode):
            states.append(_FileState(path, None, None, []))
            continue
        directory = path.parent
        if directory not in listings:
            listings[directory] = list_directory(directory)
        # Matched against the file's own stem, not the canonical one: a
        # `relative_path` can point at a hand-renamed file (or one written by
        # another tool) that doesn't follow this app's naming scheme at all,
        # and sidecars sitting next to it follow *its* name.
        states.append(
            _FileState(
                path,
                stat.st_size,
                stat.st_mtime_ns,
                match_sidecar_subtitles(listings[directory], path.stem, exclude=path),
            )
        )
    return states


def _relative_path(path: Path, relative_to: Path) -> str:
    try:
        return str(path.relative_to(relative_to))
    except ValueError:
        # A library root that isn't a parent of the file (misconfigured, or
        # moved since import). Report the bare filename rather than the
        # absolute path - this value is served to API clients, which have no
        # business seeing the host's directory layout.
        return path.name
