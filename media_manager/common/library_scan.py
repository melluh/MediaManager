"""
Reconciling the media file records in the database with what is actually on
disk.

Two things drift apart over time: records written before their path was
persisted still have `relative_path = NULL` and can only be found by their
expected filename, and files dropped into a media directory by hand have no
record at all. The scan heals both - it relinks records to the file they
match, clears the path of records whose file is gone, and adopts unclaimed
video files as new records.

The scan never deletes a file record and never touches a media item whose
root directory is missing: an unmounted volume must not be read as "every
file vanished".

Discovery is a recursive walk of the media item's root directory, so a
library laid out by hand ("Season 01", "S01", everything in one folder) is
found just as well as one this app wrote itself.

The decision-making is a pure function (`plan_media_scan`) over a directory
listing plus the media item's existing records, so it can be exercised
against real files without a database. Applying a plan - the writes - is the
service layer's job.
"""

import asyncio
import logging
import os
from collections.abc import Callable, Hashable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from media_manager.common.media_files import (
    DirectoryEntry,
    is_video_file,
    list_directory,
)
from media_manager.torrent.schemas import Quality
from media_manager.torrent.utils import remove_special_characters
from media_manager.torrent.video_probe import probe_video_files, resolve_file_quality

log = logging.getLogger(__name__)

_SUFFIX_SEPARATOR = " - "


class LibraryScanCounts(BaseModel):
    """What a scan of one media type changed."""

    items_scanned: int = 0
    items_skipped: int = 0
    """Media items whose root directory was missing, and were left untouched."""
    paths_relinked: int = 0
    paths_cleared: int = 0
    files_adopted: int = 0


class LibraryScanSummary(BaseModel):
    """Result of scanning the whole library, per media type."""

    movies: LibraryScanCounts = Field(default_factory=LibraryScanCounts)
    tv: LibraryScanCounts = Field(default_factory=LibraryScanCounts)


@dataclass(frozen=True)
class AdoptionOwner:
    """The record owner an unclaimed file on disk belongs to."""

    key: Hashable
    """Identifies the row the new file record hangs off: a movie or an episode."""
    canonical_stem: str
    """The owner's unsuffixed filename stem, which a file's suffix is derived against."""


@dataclass(frozen=True)
class ScanRecord:
    """An existing media file record, as the scan needs to see it."""

    owner_key: Hashable
    """The movie or episode the record belongs to; file path suffixes are unique per owner."""
    stem: str
    """Expected filename without extension, including the record's `file_path_suffix`."""
    file_path_suffix: str
    relative_path: str | None


@dataclass(frozen=True)
class ScanTarget:
    """One media item to scan."""

    media_root: Path
    """Directory holding this item's files, walked recursively."""
    records: Sequence[ScanRecord]
    adopt: Callable[[Path], AdoptionOwner | None]
    """Maps an unclaimed file to its owner, or None to leave it alone."""


@dataclass(frozen=True)
class ScanListing:
    """What one media item's directories held when the scan read them."""

    listings: dict[Path, list[DirectoryEntry]]
    """Every directory that was listed, including any lying outside the media root."""
    walked: tuple[Path, ...]
    """
    The media root and its subdirectories, in a stable order. Only files found
    here may be matched to a record or adopted; the extra listings exist purely
    so a record pointing outside the root still counts as having its file.
    """


@dataclass(frozen=True)
class PathUpdate:
    """A record whose stored `relative_path` no longer matches reality."""

    record: ScanRecord
    relative_path: str | None


@dataclass
class Adoption:
    """A video file on disk that no record claims, to be stored as a new one."""

    owner_key: Hashable
    file_path_suffix: str
    relative_path: str
    path: Path
    quality: Quality = Quality.unknown
    """Filled in from the file's probe once the whole scan's files are probed together."""


@dataclass
class MediaScanPlan:
    """The changes one media item's files call for."""

    skipped: bool = False
    """The media root was missing, so nothing was inspected and nothing changes."""
    relinked: list[PathUpdate] = field(default_factory=list)
    cleared: list[PathUpdate] = field(default_factory=list)
    adoptions: list[Adoption] = field(default_factory=list)


def collect_listings(target: ScanTarget) -> ScanListing | None:
    """
    Reads everything the target's files can be found in: a recursive walk of
    the media root, plus the directory of any stored path that falls outside
    it.

    Returns None when the media root does not exist - the caller must then
    skip the item rather than treat its files as gone.

    :param target: The media item to list directories for.
    :return: What was found on disk, or None if the root is missing.
    """
    if not target.media_root.is_dir():
        return None

    listings: dict[Path, list[DirectoryEntry]] = {
        directory: list_directory(directory)
        for directory in _walk_directories(target.media_root)
    }
    walked = tuple(listings)

    # A record can point outside the media root (a hand-edited path, a
    # leftover from an older layout). Listing those directories too keeps such
    # a record linked to its file instead of having its path cleared for being
    # unlistable.
    for record in target.records:
        if not record.relative_path:
            continue
        directory = (target.media_root / record.relative_path).parent
        if directory not in listings:
            listings[directory] = list_directory(directory)

    return ScanListing(listings=listings, walked=walked)


def plan_media_scan(
    target: ScanTarget,
    listing: ScanListing | None,
) -> MediaScanPlan:
    """
    Decides what one media item's scan changes, without touching the database
    or the filesystem.

    :param target: The media item and its existing records.
    :param listing: What `collect_listings` read, or None when the media root
        is missing.
    :return: The changes to apply.
    """
    if listing is None:
        return MediaScanPlan(skipped=True)

    present = {
        entry.path for entries in listing.listings.values() for entry in entries
    }
    plan = MediaScanPlan()
    claimed: set[Path] = set()
    unresolved: list[ScanRecord] = []

    # Records that already know where their file is claim it first, so a
    # record still looking for one cannot steal it by stem match.
    for record in target.records:
        path = (
            target.media_root / record.relative_path if record.relative_path else None
        )
        if path is not None and path in present:
            claimed.add(path)
        else:
            unresolved.append(record)

    for record in unresolved:
        path = _match_stem_anywhere(listing, record.stem, claimed)
        if path is None:
            # Writing NULL over NULL is not a change, and would make a second
            # scan report work it did not do.
            if record.relative_path is not None:
                plan.cleared.append(PathUpdate(record=record, relative_path=None))
            continue
        claimed.add(path)
        plan.relinked.append(
            PathUpdate(
                record=record, relative_path=_relative_to(path, target.media_root)
            )
        )

    plan.adoptions = _plan_adoptions(target=target, listing=listing, claimed=claimed)
    return plan


async def scan_media_targets(targets: Sequence[ScanTarget]) -> list[MediaScanPlan]:
    """
    Plans the scan of every given media item: all filesystem work in one
    worker thread, then a single batched probe of everything being adopted.

    :param targets: The media items to scan.
    :return: One plan per target, in the same order.
    """
    plans = await asyncio.to_thread(_plan_all, targets)

    adoptions = [adoption for plan in plans for adoption in plan.adoptions]
    probes = await probe_video_files(adoption.path for adoption in adoptions)
    for adoption, probe in zip(adoptions, probes, strict=True):
        adoption.quality = resolve_file_quality(
            probe.quality, adoption.path.name, Quality.unknown
        )
    return plans


def count_plans(plans: Sequence[MediaScanPlan]) -> LibraryScanCounts:
    """
    Aggregates plans into the counts reported for a media type.

    :param plans: The plans produced for one media type.
    :return: The counts describing them.
    """
    return LibraryScanCounts(
        items_scanned=sum(1 for plan in plans if not plan.skipped),
        items_skipped=sum(1 for plan in plans if plan.skipped),
        paths_relinked=sum(len(plan.relinked) for plan in plans),
        paths_cleared=sum(len(plan.cleared) for plan in plans),
        files_adopted=sum(len(plan.adoptions) for plan in plans),
    )


def _plan_all(targets: Sequence[ScanTarget]) -> list[MediaScanPlan]:
    return [plan_media_scan(target, collect_listings(target)) for target in targets]


def _walk_directories(root: Path) -> Iterator[Path]:
    """
    The media root and every directory below it, parents before children and
    siblings in name order, so two scans of an unchanged tree agree.
    """
    for parent, subdirectories, _ in os.walk(root):
        subdirectories.sort()
        yield Path(parent)


def _match_stem_anywhere(
    listing: ScanListing, stem: str, claimed: set[Path]
) -> Path | None:
    """
    The unclaimed file matching a record's expected filename, from anywhere
    under the media root rather than only where the record was written. That
    width is what lets a record in a hand-made layout relink instead of having
    its path cleared.

    Several files can match one record; a video file wins over a sidecar, and
    ties break on the path, so repeat scans keep choosing the same one.
    """
    prefix = f"{stem}."
    candidates = [
        entry.path
        for directory in listing.walked
        for entry in listing.listings.get(directory, ())
        if entry.path.name.startswith(prefix) and entry.path not in claimed
    ]
    candidates.sort(key=lambda path: (not is_video_file(path), path))
    return next(iter(candidates), None)


def _plan_adoptions(
    target: ScanTarget,
    listing: ScanListing,
    claimed: set[Path],
) -> list[Adoption]:
    used_suffixes: dict[Hashable, set[str]] = {}
    for record in target.records:
        used_suffixes.setdefault(record.owner_key, set()).add(record.file_path_suffix)

    adoptions: list[Adoption] = []
    for directory in listing.walked:
        for entry in listing.listings.get(directory, ()):
            path = entry.path
            if path in claimed or not is_video_file(path):
                continue
            owner = target.adopt(path)
            if owner is None:
                continue
            used = used_suffixes.setdefault(owner.key, set())
            suffix = _unique_suffix(
                _derive_suffix(path.stem, owner.canonical_stem), used
            )
            used.add(suffix)
            adoptions.append(
                Adoption(
                    owner_key=owner.key,
                    file_path_suffix=suffix,
                    relative_path=_relative_to(path, target.media_root),
                    path=path,
                )
            )
    return adoptions


def _derive_suffix(file_stem: str, canonical_stem: str) -> str:
    """
    The file path suffix an adopted file gets: whatever distinguishes its name
    from the canonical name for that media, or the whole stem for a file named
    something else entirely. An empty suffix is what an unsuffixed canonical
    file gets.
    """
    if file_stem.startswith(canonical_stem):
        suffix = file_stem[len(canonical_stem) :].removeprefix(_SUFFIX_SEPARATOR)
    else:
        suffix = file_stem
    # The suffix is written back into filenames on the next import, so it is
    # sanitized the same way an imported one is.
    return remove_special_characters(suffix)


def _unique_suffix(suffix: str, used: set[str]) -> str:
    """
    The suffix is half a file record's primary key, so it has to be unique
    per media item even when two files disagree.
    """
    candidate = suffix
    counter = 2
    while candidate in used:
        # Stripped so an empty base suffix yields "(2)" rather than " (2)",
        # which would end up as a doubled separator in a filename.
        candidate = f"{suffix} ({counter})".strip()
        counter += 1
    return candidate


def _relative_to(path: Path, media_root: Path) -> str:
    return str(path.relative_to(media_root))
