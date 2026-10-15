import logging
from datetime import datetime
from typing import Any, override
from urllib.parse import quote

import httpx

from media_manager.common.cache import AsyncTTLCache
from media_manager.config import get_config
from media_manager.mediaServer.abstract_media_server_provider import (
    AbstractMediaServerProvider,
)
from media_manager.mediaServer.schemas import MediaServerUser, PlayedMediaItem

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

_NOT_FOUND_STATUSES = {400, 404}
"""Responses meaning "no such item" rather than a broken server - Jellyfin
answers 400 instead of 404 for an id that isn't a valid GUID."""

_PLAYED_ITEMS_LIMIT = 50
"""Most recently played movies fetched when looking for ones to ask the user
about - far more than anyone watches within the lookback window."""

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

    async def __get(self, path: str, params: dict | None = None) -> Any:  # noqa: ANN401 # parsed JSON body
        try:
            response = await _client.get(
                url=f"{self.url}{path}",
                headers={"Authorization": f"MediaBrowser Token={self.api_key}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # The server answered, so a lookup for something that doesn't
            # exist says nothing about its health.
            if e.response.status_code not in _NOT_FOUND_STATUSES:
                self._report_unavailable(f"Request failed: {e}")
            raise
        except Exception as e:
            self._report_unavailable(f"Request failed: {e}")
            raise

    async def __get_items(self, params: dict) -> dict:
        return await self.__get("/Items", params)

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
        # Deliberately not caught here: a lookup this raises out of is never
        # written into `_watch_url_cache` (see `find_watch_url`), so a
        # transient failure (e.g. a bad API key) can't get cached as a false
        # "not in library" for `_CACHE_TTL_SECONDS`. The caller logs it.
        data = await self.__get_items(
            {
                "AnyProviderIdEquals": provider_id_query,
                "Recursive": "true",
                "IncludeItemTypes": "Movie,Series",
                "Fields": "ProviderIds",
                "Limit": _SEARCH_PAGE_SIZE,
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

        # AnyProviderIdEquals doesn't reliably filter on every Jellyfin
        # version - if there are more items in the library than we fetched,
        # the page we got can't be trusted to be exhaustive.
        if data.get("TotalRecordCount", 0) > len(items):
            return await self.__scan_full_library(
                imdb_id, external_id, metadata_provider
            )
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

    @override
    async def list_users(self) -> list[MediaServerUser]:
        users = await self.__get("/Users")
        return [MediaServerUser(id=user["Id"], name=user["Name"]) for user in users]

    @override
    async def get_user(self, user_id: str) -> MediaServerUser | None:
        try:
            user = await self.__get(f"/Users/{quote(user_id, safe='')}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in _NOT_FOUND_STATUSES:
                return None
            raise
        return MediaServerUser(id=user["Id"], name=user["Name"])

    @override
    async def get_recently_played_movies(
        self, user_id: str, since: datetime
    ) -> list[PlayedMediaItem]:
        data = await self.__get_items(
            {
                "userId": user_id,
                "IsPlayed": "true",
                "IncludeItemTypes": "Movie",
                "Recursive": "true",
                "SortBy": "DatePlayed",
                "SortOrder": "Descending",
                "Fields": "ProviderIds",
                "EnableUserData": "true",
                "Limit": _PLAYED_ITEMS_LIMIT,
            }
        )
        played = []
        for item in data.get("Items", []):
            # Items marked as played by hand may have no play date.
            last_played = (item.get("UserData") or {}).get("LastPlayedDate")
            if not last_played:
                continue
            last_played_at = datetime.fromisoformat(last_played)
            if last_played_at < since:
                break
            provider_ids = {
                key.lower(): str(value)
                for key, value in (item.get("ProviderIds") or {}).items()
                if value
            }
            played.append(
                PlayedMediaItem(
                    provider_ids=provider_ids, last_played_at=last_played_at
                )
            )
        return played

    @override
    async def ping(self) -> bool:
        # /System/Info requires authentication, so this also catches a bad API key.
        try:
            await self.__get("/System/Info")
        except Exception:  # noqa: BLE001 # ping should report failure for any reason
            return False
        else:
            return True
