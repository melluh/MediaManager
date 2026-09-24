import asyncio
from dataclasses import dataclass
from typing import Any

import media_manager.metadataProvider.utils
from media_manager.common.ranking import ScoredEntry, derive_title_fields, rank_entries
from media_manager.common.repository import BaseRepository, EntityId
from media_manager.metadataProvider.abstract_metadata_provider import (
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult
from media_manager.search.config import SearchConfig
from media_manager.search.schemas import CombinedSearchResult, MediaType, SearchResult
from media_manager.titleIndex.service import TitleSuggestionService


@dataclass(slots=True)
class _LibraryCandidate:
    """Rankable projection of one library row - see `Rankable` in `media_manager.common.ranking`."""

    id: EntityId
    media_type: MediaType
    normalized: str
    acronym_full: str
    acronym_no_article: str
    popularity_pct: float


class SearchService:
    """
    Aggregates local-database search results across media types, and (via
    `combined_search`) merges them with not-yet-in-library title-index
    suggestions into one ranked list.

    To support an additional media type, add its repository (any
    `BaseRepository` subclass whose model uses `MediaMixin`) to the
    `repositories` mapping passed in on construction.
    """

    def __init__(
        self,
        repositories: dict[MediaType, BaseRepository[Any, Any]],
        title_suggestion_service: TitleSuggestionService,
        config: SearchConfig,
    ) -> None:
        self.repositories = repositories
        self.title_suggestion_service = title_suggestion_service
        self.config = config

    async def _scored_library_candidates(
        self, query: str
    ) -> list[ScoredEntry[_LibraryCandidate]]:
        """
        Ranks every library row (across all media types together, not a
        fixed per-type quota) via the same fuzzy/acronym logic the title
        index uses - typo and abbreviation tolerance for already-added
        media (e.g. "lotr" finding an added "The Lord of the Rings"), which
        plain `ILIKE` never provided.

        Popularity doesn't apply to library items (there's no such column,
        and none should be simulated), so every candidate gets the same
        flat constant through the ranker's popularity slot - see
        `SearchConfig.library_match_bonus` for why that's fine (it only
        needs to be *uniform*, not calibrated) and `combined_search` for how
        library-vs-not-library precedence is actually decided.
        """
        candidates: list[_LibraryCandidate] = []
        normalized_titles: list[str] = []
        for media_type, repository in self.repositories.items():
            rows = await repository.get_all_names()
            for row in rows:
                normalized, acronym_full, acronym_no_article = derive_title_fields(row.name)
                candidates.append(
                    _LibraryCandidate(
                        id=row.id,
                        media_type=media_type,
                        normalized=normalized,
                        acronym_full=acronym_full,
                        acronym_no_article=acronym_no_article,
                        popularity_pct=self.config.library_match_bonus,
                    )
                )
                normalized_titles.append(normalized)

        if not candidates:
            return []
        return rank_entries(
            candidates,
            normalized_titles,
            query,
            score_cutoff=self.config.score_cutoff,
            # Uncapped: the library pool is small (nothing like the 150k-row
            # title index), and truncating it here would silently drop the
            # actual best library match before this score ever gets
            # compared against the title-index pool in combined_search.
            candidate_limit=len(candidates),
        )

    async def _hydrate_library_results(
        self, scored: list[ScoredEntry[_LibraryCandidate]]
    ) -> list[SearchResult]:
        """
        Fetches full display fields for exactly `scored`'s winners (not the
        whole library), and returns them in `scored`'s order.
        """
        if not scored:
            return []

        ids_by_media_type: dict[MediaType, list[EntityId]] = {}
        for item in scored:
            ids_by_media_type.setdefault(item.entry.media_type, []).append(item.entry.id)

        rows_by_id: dict[EntityId, Any] = {}
        for media_type, ids in ids_by_media_type.items():
            repository = self.repositories[media_type]
            for row in await repository.get_by_ids_for_search(ids):
                rows_by_id[row.id] = row

        results: list[SearchResult] = []
        for item in scored:
            row = rows_by_id.get(item.entry.id)
            if row is None:
                continue  # deleted between the ranking query and this one
            results.append(SearchResult(**row.model_dump(), media_type=item.entry.media_type))

        images_by_id = await asyncio.to_thread(
            media_manager.metadataProvider.utils.get_available_media_images_many,
            [result.id for result in results],
        )
        for result in results:
            result.images = images_by_id[str(result.id)]
        return results

    async def search(self, query: str) -> list[SearchResult]:
        scored = await self._scored_library_candidates(query)
        return await self._hydrate_library_results(scored[: self.config.max_results])

    @staticmethod
    def _dedupe_suggestions_by_title(
        merged: list[tuple[ScoredEntry[Any], bool]],
    ) -> list[tuple[ScoredEntry[Any], bool]]:
        """
        Keeps only the best-ranked not-in-library suggestion per (media_type, normalized title).
        The title index doesn't show release year, so two titles from different years look identical.
        Library items aren't collapsed as they're always distinct (and easily distinguishable) items.
        """
        seen: set[tuple[MediaType, str]] = set()
        deduped: list[tuple[ScoredEntry[Any], bool]] = []
        for item, in_library in merged:
            if not in_library:
                key = (item.entry.media_type, item.entry.normalized)
                if key in seen:
                    continue
                seen.add(key)
            deduped.append((item, in_library))
        return deduped

    async def combined_search(self, query: str) -> list[CombinedSearchResult]:
        """
        Merges the library pool and the not-in-library title-index pool
        into one ranked list. Each pool is ranked independently (each with
        its own appropriate candidate limit) and only merged afterwards -
        concatenating the pools before ranking would let the title index's
        much larger candidate set crowd library rows out of rapidfuzz's
        `limit` before this merge ever gets a say, silently dropping matches
        ILIKE would have found.

        The merge sorts on `(is_structural, in_library, tier_score)`:
        in-library results always outrank not-in-library results of the
        *same* match quality (both structural, or both fuzzy-only), and a
        not-in-library *structural* match still outranks a library
        *fuzzy-only* (typo-level) match. `in_library` is an explicit tier
        here rather than folded into `tier_score` via some "in-library
        bonus" competing numerically against real popularity - that was
        tried and didn't hold up: TMDB popularity percentiles over a
        ~150k-title pool are generously distributed enough (many ordinary,
        moderately-known titles land in the 90th+ percentile) that no fixed
        bonus reliably kept genuine in-library matches on top without also
        being fragile (only a bonus at the theoretical maximum, 100, ever
        consistently won, and even then only by the slimmest of margins
        against a title at the 99.9th percentile).
        """
        library_scored = await self._scored_library_candidates(query)
        title_index_scored = await self.title_suggestion_service.scored_candidates_excluding_library(
            query
        )

        merged: list[tuple[ScoredEntry[Any], bool]] = [
            (item, True) for item in library_scored
        ] + [(item, False) for item in title_index_scored]
        merged.sort(
            key=lambda pair: (pair[0].is_structural, pair[1], pair[0].tier_score),
            reverse=True,
        )
        merged = self._dedupe_suggestions_by_title(merged)[: self.config.max_results]

        library_winners = [item for item, in_library in merged if in_library]
        hydrated_by_id = {
            result.id: result for result in await self._hydrate_library_results(library_winners)
        }

        combined: list[CombinedSearchResult] = []
        for item, in_library in merged:
            if in_library:
                hydrated = hydrated_by_id.get(item.entry.id)
                if hydrated is None:
                    continue
                combined.append(
                    CombinedSearchResult(
                        in_library=True,
                        media_type=hydrated.media_type,
                        name=hydrated.name,
                        id=hydrated.id,
                        slug=hydrated.slug,
                        year=hydrated.year,
                        runtime=hydrated.runtime,
                        genres=hydrated.genres,
                        images=hydrated.images,
                        metadata_updated_at=hydrated.metadata_updated_at,
                    )
                )
            else:
                entry = item.entry
                combined.append(
                    CombinedSearchResult(
                        in_library=False,
                        media_type=entry.media_type,
                        name=entry.title,
                        external_id=entry.id,
                        popularity=entry.popularity,
                    )
                )
        return combined

    async def search_external(
        self,
        query: str,
        metadata_provider: AbstractMetadataProvider,
    ) -> list[MetaDataProviderSearchResult]:
        """
        Search the metadata provider for movies and TV shows together (via
        its combined multi-search), excluding results already in the local
        library (they're already covered by `search`).

        Also de-duplicates by (media_type, external_id): a provider's
        multi-search can return the same item more than once across pages
        for broad queries (e.g. ranking shifting slightly between page
        fetches), which would otherwise reach the frontend as duplicate
        list keys.
        """
        raw_results = await metadata_provider.search_multi(query=query)
        results: list[MetaDataProviderSearchResult] = []
        seen: set[tuple[MediaType, int]] = set()
        for result in raw_results:
            dedupe_key = (result.media_type, result.external_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            repository = self.repositories.get(result.media_type)
            if repository is not None and await repository.exists_by_external_id(
                external_id=result.external_id,
                metadata_provider=metadata_provider.name,
            ):
                continue  # already in the library

            results.append(result)
        return results
