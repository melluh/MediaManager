import asyncio
import gzip
import json
from dataclasses import dataclass
from pathlib import Path

from media_manager.common.ranking import ScoredEntry, derive_title_fields
from media_manager.common.ranking import rank_entries as _rank_entries
from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.download import FINAL_FILENAME


@dataclass(slots=True)
class IndexEntry:
    id: int
    title: str
    normalized: str
    popularity: float
    media_type: MediaType
    acronym_full: str
    acronym_no_article: str
    popularity_pct: float


_entries: list[IndexEntry] = []
_normalized_titles: list[str] = []
_loaded_mtime: float | None = None
_load_lock = asyncio.Lock()


def _derive_entries(path: Path) -> tuple[list[IndexEntry], list[str]]:
    """
    Loads the compact on-disk artifact and derives everything scoring needs
    (normalized title, acronym variants, popularity percentile) in one pass.
    Kept out of the persisted artifact so normalizer/acronym-logic changes
    take effect immediately, without needing to touch the file format.
    """
    raw_rows: list[dict] = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if line:
                raw_rows.append(json.loads(line))

    total = len(raw_rows)
    entries: list[IndexEntry] = []
    normalized_titles: list[str] = []
    for position, row in enumerate(raw_rows):
        normalized, acronym_full, acronym_no_article = derive_title_fields(row["t"])
        # `raw_rows` is already popularity-descending (see download.py), so
        # position doubles as a popularity rank without re-sorting.
        popularity_pct = 100.0 * (1 - position / total) if total else 0.0

        entries.append(
            IndexEntry(
                id=row["id"],
                title=row["t"],
                normalized=normalized,
                popularity=row["p"],
                media_type=MediaType(row["m"]),
                acronym_full=acronym_full,
                acronym_no_article=acronym_no_article,
                popularity_pct=popularity_pct,
            )
        )
        normalized_titles.append(normalized)
    return entries, normalized_titles


async def _ensure_loaded(directory: Path) -> tuple[list[IndexEntry], list[str]]:
    global _entries, _normalized_titles, _loaded_mtime

    path = directory / FINAL_FILENAME
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return [], []

    if mtime == _loaded_mtime:
        return _entries, _normalized_titles

    async with _load_lock:
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError:
            return [], []
        if mtime == _loaded_mtime:
            return _entries, _normalized_titles

        entries, normalized_titles = await asyncio.to_thread(_derive_entries, path)
        _entries, _normalized_titles, _loaded_mtime = entries, normalized_titles, mtime
        return _entries, _normalized_titles


def scored_entries(
    entries: list[IndexEntry],
    normalized_titles: list[str],
    query: str,
    config: TitleIndexConfig,
) -> list[ScoredEntry[IndexEntry]]:
    """
    Ranks title-index entries via the shared `media_manager.common.ranking`
    logic, returning scored (not-yet-unwrapped) results so a caller can
    merge them against another pool's scored candidates - see
    `media_manager.search.service.SearchService.combined_search`.
    """
    return _rank_entries(
        entries,
        normalized_titles,
        query,
        score_cutoff=config.score_cutoff,
        candidate_limit=config.candidate_limit,
    )


def rank_entries(
    entries: list[IndexEntry],
    normalized_titles: list[str],
    query: str,
    config: TitleIndexConfig,
) -> list[IndexEntry]:
    """Backward-compatible wrapper over `scored_entries`, unwrapped to a plain ranked list."""
    return [scored.entry for scored in scored_entries(entries, normalized_titles, query, config)]


async def suggest_scored(
    directory: Path, query: str, config: TitleIndexConfig
) -> list[ScoredEntry[IndexEntry]]:
    entries, normalized_titles = await _ensure_loaded(directory)
    if not entries:
        return []
    return await asyncio.to_thread(scored_entries, entries, normalized_titles, query, config)


async def suggest(directory: Path, query: str, config: TitleIndexConfig) -> list[IndexEntry]:
    scored = await suggest_scored(directory, query, config)
    return [item.entry for item in scored]
