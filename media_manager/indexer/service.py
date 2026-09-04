import asyncio
import logging

from media_manager.common.cache import AsyncTTLCache
from media_manager.config import MediaManagerConfig
from media_manager.exceptions import InvalidConfigError
from media_manager.indexer.indexers.generic import GenericIndexer
from media_manager.indexer.indexers.jackett import Jackett
from media_manager.indexer.indexers.prowlarr import Prowlarr
from media_manager.indexer.repository import IndexerRepository
from media_manager.indexer.schemas import IndexerQueryResult, IndexerQueryResultId
from media_manager.movies.schemas import Movie
from media_manager.torrent.utils import remove_special_chars_and_parentheses
from media_manager.tv.schemas import Show

log = logging.getLogger(__name__)

# Module-level because IndexerService is instantiated fresh per request.
_search_cache: AsyncTTLCache[tuple[object, ...], list[IndexerQueryResult]] = (
    AsyncTTLCache(
        ttl_seconds=MediaManagerConfig().indexers.search_cache_ttl_minutes * 60,
        max_size=2000,
    )
)

class IndexerService:
    def __init__(self, indexer_repository: IndexerRepository) -> None:
        config = MediaManagerConfig()
        self.repository = indexer_repository
        self.indexers: list[GenericIndexer] = []

        if config.indexers.prowlarr.enabled:
            self.indexers.append(Prowlarr())
        if config.indexers.jackett.enabled:
            self.indexers.append(Jackett())

    def _require_indexers(self) -> None:
        if not self.indexers:
            msg = "No indexers configured. Configure an indexer (e.g. Prowlarr or Jackett) in the config file."
            raise InvalidConfigError(msg)

    async def get_result(self, result_id: IndexerQueryResultId) -> IndexerQueryResult:
        return await self.repository.get_result(result_id=result_id)

    async def search(self, query: str, is_tv: bool) -> list[IndexerQueryResult]:
        """
        Search for results using the indexers based on a query.

        :param is_tv: Whether the search is for TV shows or movies.
        :param query: The search query, is used as a fallback in case indexers don't support e.g. TMDB ID based search.
        :return: A list of search results.
        """
        self._require_indexers()
        log.debug(f"Searching for: {query}")
        normalized_query = query.strip().lower()
        cache_key = ("adhoc", normalized_query, is_tv)

        async def factory() -> list[IndexerQueryResult]:
            results = []

            for indexer in self.indexers:
                try:
                    indexer_results = await asyncio.to_thread(
                        indexer.search, normalized_query, is_tv=is_tv
                    )
                    results.extend(indexer_results)
                    log.debug(
                        f"Indexer {indexer.__class__.__name__} returned {len(indexer_results)} results for query: {normalized_query}"
                    )
                except Exception:
                    log.exception(
                        f"Indexer {indexer.__class__.__name__} failed for query '{normalized_query}'"
                    )

            for result in results:
                await self.repository.save_result(result=result)

            return results

        cached_results = await _search_cache.get_or_set(cache_key, factory)
        return [result.model_copy() for result in cached_results]

    async def search_movie(self, movie: Movie) -> list[IndexerQueryResult]:
        self._require_indexers()
        query = f"{movie.name} {movie.year}"
        query = remove_special_chars_and_parentheses(query)
        cache_key = ("movie", query)

        async def factory() -> list[IndexerQueryResult]:
            results = []
            for indexer in self.indexers:
                try:
                    indexer_results = await asyncio.to_thread(
                        indexer.search_movie, query=query, movie=movie
                    )
                    if indexer_results:
                        results.extend(indexer_results)
                except Exception:
                    log.exception(
                        f"Indexer {indexer.__class__.__name__} failed for movie search '{query}'"
                    )

            for result in results:
                await self.repository.save_result(result=result)

            return results

        cached_results = await _search_cache.get_or_set(cache_key, factory)
        return [result.model_copy() for result in cached_results]

    async def search_season(
        self, show: Show, season_number: int
    ) -> list[IndexerQueryResult]:
        self._require_indexers()
        query = f"{show.name} {show.year} S{season_number:02d}"
        query = remove_special_chars_and_parentheses(query)
        cache_key = ("season", query)

        async def factory() -> list[IndexerQueryResult]:
            results = []
            for indexer in self.indexers:
                try:
                    indexer_results = await asyncio.to_thread(
                        indexer.search_season,
                        query=query,
                        show=show,
                        season_number=season_number,
                    )
                    if indexer_results:
                        results.extend(indexer_results)
                except Exception:
                    log.exception(
                        f"Indexer {indexer.__class__.__name__} failed for season search '{query}'"
                    )

            for result in results:
                await self.repository.save_result(result=result)

            return results

        cached_results = await _search_cache.get_or_set(cache_key, factory)
        return [result.model_copy() for result in cached_results]
