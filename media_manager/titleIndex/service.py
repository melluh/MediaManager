from pathlib import Path
from typing import Any

from media_manager.common.ranking import ScoredEntry
from media_manager.common.repository import BaseRepository
from media_manager.metadataProvider.schemas import MediaType
from media_manager.titleIndex import index as title_index
from media_manager.titleIndex.config import TitleIndexConfig
from media_manager.titleIndex.index import IndexEntry
from media_manager.titleIndex.schemas import TitleSuggestion


class TitleSuggestionService:
    """
    Fast, typo-tolerant title suggestions for media not yet in the library,
    sourced from the local TMDB-daily-export-backed index rather than a live
    provider call.
    """

    def __init__(
        self,
        repositories: dict[MediaType, BaseRepository[Any, Any]],
        directory: Path,
        config: TitleIndexConfig,
    ) -> None:
        self.repositories = repositories
        self.directory = directory
        self.config = config

    async def scored_candidates_excluding_library(
        self, query: str
    ) -> list[ScoredEntry[IndexEntry]]:
        """
        Every title-index candidate for `query`, scored, with items already
        in the library excluded - but not sliced to `max_results` or mapped
        to `TitleSuggestion`. Used both by `suggest` below and by
        `media_manager.search.service.SearchService.combined_search`, which
        merges these scored candidates against a separately-ranked library
        pool before slicing.
        """
        scored = await title_index.suggest_scored(self.directory, query, self.config)
        if not scored:
            return []

        ids_by_media_type: dict[MediaType, list[int]] = {}
        for item in scored:
            ids_by_media_type.setdefault(item.entry.media_type, []).append(item.entry.id)

        in_library: set[tuple[MediaType, int]] = set()
        for media_type, external_ids in ids_by_media_type.items():
            repository = self.repositories.get(media_type)
            if repository is None:
                continue
            found = await repository.get_ids_by_external_ids(
                external_ids=external_ids, metadata_provider="tmdb"
            )
            in_library.update((media_type, external_id) for external_id in found)

        return [
            item
            for item in scored
            if (item.entry.media_type, item.entry.id) not in in_library
        ]

    async def suggest(self, query: str) -> list[TitleSuggestion]:
        scored = await self.scored_candidates_excluding_library(query)
        return [
            TitleSuggestion(
                id=item.entry.id,
                title=item.entry.title,
                media_type=item.entry.media_type,
                popularity=item.entry.popularity,
            )
            for item in scored[: self.config.max_results]
        ]
