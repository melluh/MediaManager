import asyncio
import gzip
import json
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz, process

from media_manager.common.import_match import normalize_title
from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.download import FINAL_FILENAME

_ARTICLES = ("the", "a", "an")


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


def _acronym(tokens: list[str]) -> str:
    return "".join(token[0] for token in tokens if token)


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
        normalized = normalize_title(row["t"])
        tokens = normalized.split(" ") if normalized else []
        acronym_full = _acronym(tokens)
        no_article_tokens = tokens[1:] if tokens and tokens[0] in _ARTICLES else tokens
        acronym_no_article = _acronym(no_article_tokens)
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


_ACRONYM_PROXY_SCORE = 90.0


def rank_entries(
    entries: list[IndexEntry],
    normalized_titles: list[str],
    query: str,
    config: TitleIndexConfig,
) -> list[IndexEntry]:
    """
    Pure ranking step, independent of disk-loading/locking, so it's directly
    testable against a small hand-built entry list.

    Splits candidates into two tiers rather than blending every signal into
    one formula (validated against a real ~150k-entry TMDB index - see PR
    description):

    - "Structural" matches - the query is a prefix of the title or one of
      its words, or matches an acronym (e.g. "lotr" -> "The Lord of the
      Rings", "got" -> "Game of Thrones") - already have relevance
      established by that relationship, so popularity decides which one the
      user most likely means; rapidfuzz's score only breaks near-ties (e.g.
      an exact match vs. a longer prefix). Blending fuzzy score in at full
      strength here let a merely-exact-but-obscure title ("Matrix", a small
      show) outrank a hugely more popular prefix match ("The Matrix").
    - Everything else is a typo/near-miss with no structural relationship to
      lean on, so closeness of the text match must dominate, with popularity
      only breaking ties between similarly-close matches.

    Structural matches always rank above fuzzy-only ones.
    """
    normalized_query = normalize_title(query)
    if not normalized_query or not entries:
        return []

    is_acronym_query = normalized_query.isalpha() and 2 <= len(normalized_query) <= 6
    acronym_hits: set[int] = set()
    scored: dict[int, float] = {}

    if is_acronym_query:
        for index, entry in enumerate(entries):
            if normalized_query in (entry.acronym_full, entry.acronym_no_article):
                scored[index] = _ACRONYM_PROXY_SCORE
                acronym_hits.add(index)

    # Plain `ratio` (not `WRatio`) deliberately: WRatio's partial-ratio
    # branch gives short candidate titles spuriously high scores against
    # short queries (e.g. "lotr" vs. an unrelated 2-letter title), which
    # popularity weighting alone can't filter back out.
    matches = process.extract(
        normalized_query,
        normalized_titles,
        scorer=fuzz.ratio,
        score_cutoff=config.score_cutoff,
        limit=config.candidate_limit,
    )
    for _choice, score, index in matches:
        scored[index] = max(scored.get(index, 0.0), score)

    ranked: list[tuple[bool, float, int]] = []
    for index, fuzzy_score in scored.items():
        entry = entries[index]
        tokens = entry.normalized.split(" ")
        is_prefix_hit = entry.normalized.startswith(normalized_query) or any(
            token.startswith(normalized_query) for token in tokens
        )
        is_structural = is_prefix_hit or index in acronym_hits
        tier_score = (
            entry.popularity_pct + 0.05 * fuzzy_score
            if is_structural
            else 0.75 * fuzzy_score + 0.25 * entry.popularity_pct
        )
        ranked.append((is_structural, tier_score, index))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [entries[index] for _is_structural, _score, index in ranked]


async def suggest(
    directory: Path, query: str, config: TitleIndexConfig
) -> list[IndexEntry]:
    entries, normalized_titles = await _ensure_loaded(directory)
    if not entries:
        return []
    return await asyncio.to_thread(rank_entries, entries, normalized_titles, query, config)
