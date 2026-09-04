import logging
from typing import override

import httpx

from media_manager.common.cache import AsyncTTLCache
from media_manager.config import get_config
from media_manager.mediaServer.abstract_media_server_provider import (
    AbstractMediaServerProvider,
)

log = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=15.0)

# Jellyfin's own provider-id keys, as found in an item's `ProviderIds` dict.
_PROVIDER_ID_KEYS = {"tmdb": "Tmdb", "tvdb": "Tvdb"}

_CACHE_TTL_SECONDS = 5 * 60
"""Short enough that a file Jellyfin just finished scanning shows up on the
next page load or two, long enough that repeated page loads don't hammer
Jellyfin's search endpoint."""

_watch_url_cache: AsyncTTLCache[tuple, str | None] = AsyncTTLCache(
    ttl_seconds=_CACHE_TTL_SECONDS, max_size=5000
)

_SEARCH_PAGE_SIZE = 25
"""Items requested from the filtered (AnyProviderIdEquals) lookup - large
enough to contain the match on the Jellyfin versions where the filter still
works."""

_FULL_SCAN_PAGE_SIZE = 500
"""Page size for the fallback full-library scan, only hit when the filtered
lookup's result doesn't contain the match (see `__find_item_id`)."""


def _matches_provider_id(
    provider_ids: dict, imdb_id: str | None, external_id: int, metadata_provider: str
) -> bool:
    if imdb_id:
        return (provider_ids.get("Imdb") or provider_ids.get("imdb")) == imdb_id

    provider_key = _PROVIDER_ID_KEYS.get(metadata_provider)
    if provider_key is None:
        return False
    value = provider_ids.get(provider_key) or provider_ids.get(metadata_provider)
    return str(value) == str(external_id) if value is not None else False


class JellyfinProvider(AbstractMediaServerProvider):
    name = "jellyfin"
    display_name = "Jellyfin"

    def __init__(self) -> None:
        config = get_config().media_server.jellyfin
        self.url = config.url.rstrip("/")
        self.external_url = (config.external_url or config.url).rstrip("/")
        self.api_key = config.api_key

    async def __get_items(self, params: dict) -> dict:
        response = await _client.get(
            url=f"{self.url}/Items",
            headers={"X-Emby-Token": self.api_key},
            params=params,
        )
        response.raise_for_status()
        return response.json()

    async def __scan_full_library(
        self, imdb_id: str | None, external_id: int, metadata_provider: str
    ) -> str | None:
        """
        Fallback for when the AnyProviderIdEquals filter isn't honored by this
        Jellyfin version (it's silently ignored on some releases, returning
        the whole unfiltered library instead of narrowing to the requested
        id) - pages the whole library once, matching ProviderIds client-side.
        """
        start = 0
        while True:
            data = await self.__get_items(
                {
                    "Recursive": "true",
                    "IncludeItemTypes": "Movie,Series",
                    "Fields": "ProviderIds",
                    "Limit": _FULL_SCAN_PAGE_SIZE,
                    "StartIndex": start,
                }
            )
            items = data.get("Items", [])
            match = next(
                (
                    item
                    for item in items
                    if _matches_provider_id(
                        item.get("ProviderIds", {}), imdb_id, external_id, metadata_provider
                    )
                ),
                None,
            )
            if match is not None:
                return match["Id"]
            start += _FULL_SCAN_PAGE_SIZE
            if start >= data.get("TotalRecordCount", 0) or not items:
                return None

    async def __find_item_id(
        self, imdb_id: str | None, external_id: int, metadata_provider: str
    ) -> str | None:
        provider_id_query = (
            f"Imdb.{imdb_id}"
            if imdb_id
            else f"{_PROVIDER_ID_KEYS.get(metadata_provider)}.{external_id}"
        )
        try:
            data = await self.__get_items(
                {
                    "AnyProviderIdEquals": provider_id_query,
                    "Recursive": "true",
                    "IncludeItemTypes": "Movie,Series",
                    "Fields": "ProviderIds",
                    "Limit": _SEARCH_PAGE_SIZE,
                }
            )
        except httpx.HTTPError:
            log.warning("Jellyfin API error looking up item", exc_info=True)
            return None

        items = data.get("Items", [])
        match = next(
            (
                item
                for item in items
                if _matches_provider_id(
                    item.get("ProviderIds", {}), imdb_id, external_id, metadata_provider
                )
            ),
            None,
        )
        if match is not None:
            return match["Id"]

        # AnyProviderIdEquals doesn't reliably filter on every Jellyfin
        # version - if there are more items in the library than we fetched,
        # the page we got can't be trusted to be exhaustive.
        if data.get("TotalRecordCount", 0) > len(items):
            try:
                return await self.__scan_full_library(
                    imdb_id, external_id, metadata_provider
                )
            except httpx.HTTPError:
                log.warning("Jellyfin API error scanning library", exc_info=True)
                return None
        return None

    @override
    async def find_watch_url(
        self,
        *,
        imdb_id: str | None,
        external_id: int,
        metadata_provider: str,
    ) -> str | None:
        if not imdb_id and metadata_provider not in _PROVIDER_ID_KEYS:
            return None

        async def factory() -> str | None:
            item_id = await self.__find_item_id(imdb_id, external_id, metadata_provider)
            if item_id is None:
                return None
            return f"{self.external_url}/web/index.html#!/details?id={item_id}"

        return await _watch_url_cache.get_or_set(
            (metadata_provider, external_id, imdb_id), factory
        )
