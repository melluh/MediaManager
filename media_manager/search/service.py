from typing import Any

from media_manager.common.repository import BaseRepository
from media_manager.metadataProvider.abstract_metadata_provider import (
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult
from media_manager.search.schemas import MediaType, SearchResult

DEFAULT_RESULTS_PER_MEDIA_TYPE = 5


class SearchService:
    """
    Aggregates local-database search results across media types.

    To support an additional media type, add its repository (any
    `BaseRepository` subclass whose model uses `MediaMixin`) to the
    `repositories` mapping passed in on construction.
    """

    def __init__(self, repositories: dict[MediaType, BaseRepository[Any, Any]]) -> None:
        self.repositories = repositories

    async def search(
        self,
        query: str,
        results_per_media_type: int = DEFAULT_RESULTS_PER_MEDIA_TYPE,
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        for media_type, repository in self.repositories.items():
            rows = await repository.search_by_name(
                query=query, limit=results_per_media_type
            )
            results.extend(
                SearchResult(
                    id=row.id,
                    media_type=media_type,
                    name=row.name,
                    overview=row.overview,
                    year=row.year,
                )
                for row in rows
            )
        return results

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
