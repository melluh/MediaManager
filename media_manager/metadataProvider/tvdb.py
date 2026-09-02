import asyncio
import logging
from datetime import UTC, datetime
from typing import override

import httpx

import media_manager.metadataProvider.utils
from media_manager.common.cache import AsyncTTLCache
from media_manager.config import MediaManagerConfig
from media_manager.metadataProvider.abstract_metadata_provider import (
    DEFAULT_SEARCH_MAX_PAGES,
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.schemas import (
    ExternalPosterImage,
    MediaImageType,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.schemas import Movie
from media_manager.notification.manager import notification_manager
from media_manager.tv.schemas import Episode, Season, SeasonNumber, Show

log = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)

_MAX_CONCURRENT_SEASON_FETCHES = 8
"""Caps concurrent per-season TVDB requests when fetching a show - a show can
have an arbitrary number of seasons, so this must not be unbounded."""

# These are module-level because TvdbMetadataProvider is instantiated fresh per
# request.
_metadata_config = MediaManagerConfig().metadata
_detail_cache: AsyncTTLCache[tuple, dict] = AsyncTTLCache(
    ttl_seconds=_metadata_config.detail_cache_ttl_hours * 3600, max_size=5000
)
_season_cache: AsyncTTLCache[tuple, dict] = AsyncTTLCache(
    ttl_seconds=_metadata_config.season_cache_ttl_hours * 3600, max_size=5000
)
_trending_cache: AsyncTTLCache[tuple, dict] = AsyncTTLCache(
    ttl_seconds=_metadata_config.trending_cache_ttl_hours * 3600, max_size=50
)


class TvdbMetadataProvider(AbstractMetadataProvider):
    name = "tvdb"

    def __init__(self) -> None:
        config = MediaManagerConfig().metadata.tvdb
        self.url = config.tvdb_relay_url

    @staticmethod
    def __get_poster_images(poster_url: str | None) -> list[ExternalPosterImage]:
        if not poster_url:
            return []
        return [ExternalPosterImage(url=poster_url)]

    async def __cached_get(
        self,
        cache: AsyncTTLCache,
        key: tuple,
        url: str,
        label: str,
        params: dict | None = None,
    ) -> dict:
        async def factory() -> dict:
            try:
                response = await _client.get(url=url, params=params, timeout=60)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                log.exception(f"TVDB API error getting {label}")
                if notification_manager.is_configured():
                    await notification_manager.send_notification(
                        title="TVDB API Error",
                        message=f"Failed to fetch {label} from TVDB. Error: {e}",
                    )
                raise

        return await cache.get_or_set(key, factory)

    async def __get_show(self, show_id: int) -> dict:
        return await self.__cached_get(
            _detail_cache,
            ("show", show_id),
            url=f"{self.url}/tv/shows/{show_id}",
            label=f"show metadata for ID {show_id}",
        )

    async def __get_season(self, show_id: int) -> dict:
        return await self.__cached_get(
            _season_cache,
            ("season", show_id),
            url=f"{self.url}/tv/seasons/{show_id}",
            label=f"season metadata for show ID {show_id}",
        )

    async def __search_tv(self, query: str) -> dict:
        try:
            response = await _client.get(
                url=f"{self.url}/tv/search", params={"query": query}, timeout=60
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TVDB API error searching TV shows with query '{query}'")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TVDB API Error",
                    message=f"Failed to search TV shows with query '{query}' on TVDB. Error: {e}",
                )
            raise

    async def __get_trending_tv(self) -> dict:
        return await self.__cached_get(
            _trending_cache,
            ("trending_tv",),
            url=f"{self.url}/tv/trending",
            label="trending TV shows",
        )

    async def __get_movie(self, movie_id: int) -> dict:
        return await self.__cached_get(
            _detail_cache,
            ("movie", movie_id),
            url=f"{self.url}/movies/{movie_id}",
            label=f"movie metadata for ID {movie_id}",
        )

    async def __search_movie(self, query: str) -> dict:
        try:
            response = await _client.get(
                url=f"{self.url}/movies/search", params={"query": query}, timeout=60
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TVDB API error searching movies with query '{query}'")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TVDB API Error",
                    message=f"Failed to search movies with query '{query}' on TVDB. Error: {e}",
                )
            raise

    async def __get_trending_movies(self) -> dict:
        return await self.__cached_get(
            _trending_cache,
            ("trending_movies",),
            url=f"{self.url}/movies/trending",
            label="trending movies",
        )

    async def __get_media(self, media: Movie | Show, media_type: MediaType) -> dict:
        if media_type == MediaType.tv:
            return await self.__get_show(show_id=media.external_id)
        return await self.__get_movie(media.external_id)

    @override
    async def get_available_image_types(
        self, media: Movie | Show, media_type: MediaType
    ) -> set[MediaImageType]:
        # TVDB backdrop artwork is not supported: the relay doesn't expose
        # artwork type information needed to reliably pick a background
        # image out of TVDB's mixed poster/banner/background artwork list.
        metadata = await self.__get_media(media, media_type)
        return {MediaImageType.poster} if metadata.get("image") else set()

    @override
    async def download_media_image(
        self, media: Movie | Show, media_type: MediaType, image_type: MediaImageType
    ) -> bool:
        if image_type is not MediaImageType.poster:
            log.debug(
                f"{image_type} images are not supported for TVDB {media_type} {media.name}"
            )
            return False

        metadata = await self.__get_media(media, media_type)
        if metadata.get("image") is None:
            log.warning(f"image for {media_type} {media.name} could not be downloaded")
            return False

        await media_manager.metadataProvider.utils.download_media_image(
            storage_path=self.storage_path,
            image_url=metadata["image"],
            media_id=media.id,
            image_type=image_type,
        )
        log.info(f"Successfully downloaded poster image for {media_type} {media.name}")
        return True

    @override
    async def get_available_season_image_types(
        self, show: Show, season: Season
    ) -> set[MediaImageType]:
        # Best-effort: not every TVDB season has its own artwork, and the
        # relay may not expose an "image" field for it at all.
        season_metadata = await self.__get_season(show_id=season.external_id)
        return {MediaImageType.poster} if season_metadata.get("image") else set()

    @override
    async def download_season_image(
        self, show: Show, season: Season, image_type: MediaImageType
    ) -> bool:
        if image_type is not MediaImageType.poster:
            log.debug(f"{image_type} images are not supported for TVDB seasons")
            return False

        season_metadata = await self.__get_season(show_id=season.external_id)
        image_url = season_metadata.get("image")
        if image_url is None:
            log.debug(
                f"poster image for {show.name} season {season.number} could not be downloaded"
            )
            return False

        await media_manager.metadataProvider.utils.download_media_image(
            storage_path=self.storage_path,
            image_url=image_url,
            media_id=season.id,
            image_type=MediaImageType.poster,
        )
        log.info(
            f"Successfully downloaded poster image for {show.name} season {season.number}"
        )
        return True

    @override
    async def get_show_metadata(
        self, show_id: int, language: str | None = None
    ) -> Show:
        """

        :param show_id: The external id of the show
        :param language: does nothing, TVDB does not support multiple languages
        """
        series = await self.__get_show(show_id)
        seasons = []
        seasons_ids = [season["id"] for season in series["seasons"]]

        # get imdb id from remote ids
        imdb_id = None
        remote_ids = series.get("remoteIds", None)
        if remote_ids:
            for remote_id in remote_ids:
                if remote_id.get("type") == 2:
                    imdb_id = remote_id.get("id")

        season_fetch_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SEASON_FETCHES)

        async def _fetch_season(season_id: int) -> dict:
            async with season_fetch_semaphore:
                return await self.__get_season(show_id=season_id)

        season_payloads = await asyncio.gather(
            *(_fetch_season(sid) for sid in seasons_ids)
        )
        for s in season_payloads:
            # Filter to "aired order" only; mixing aired/dvd orders duplicates
            # (show_id, season_number) and violates the seasons unique constraint.
            if s["type"]["id"] != 1:
                log.info(
                    f"Season {s['type']['id']} will not be downloaded because it is not a 'aired order' season"
                )
                continue

            episodes = [
                Episode(
                    number=episode["number"],
                    external_id=episode["id"],
                    title=episode["name"],
                )
                for episode in s["episodes"]
            ]
            seasons.append(
                Season(
                    number=SeasonNumber(s["number"]),
                    name="TVDB doesn't provide Season Names",
                    overview="TVDB doesn't provide Season Overviews",
                    external_id=int(s["id"]),
                    episodes=episodes,
                )
            )

        return Show(
            name=series["name"],
            overview=series["overview"],
            year=series.get("year"),
            external_id=series["id"],
            metadata_provider=self.name,
            seasons=seasons,
            ended=False,
            imdb_id=imdb_id,
            metadata_updated_at=datetime.now(UTC),
        )

    @override
    async def get_show_images(
        self, show_id: int
    ) -> tuple[list[ExternalPosterImage], list[ExternalPosterImage]]:
        series = await self.__get_show(show_id)
        # TVDB backdrop artwork is not exposed by the relay - see
        # `get_available_image_types`.
        return self.__get_poster_images(series.get("image")), []

    @override
    async def get_movie_images(
        self, movie_id: int
    ) -> tuple[list[ExternalPosterImage], list[ExternalPosterImage]]:
        movie = await self.__get_movie(movie_id)
        return self.__get_poster_images(movie.get("image")), []

    @override
    async def search_show(
        self, query: str | None = None, max_pages: int = DEFAULT_SEARCH_MAX_PAGES
    ) -> list[MetaDataProviderSearchResult]:
        """
        `max_pages` is accepted for interface parity only: TVDB's search
        returns a single, unpaginated response.
        """
        if query:
            results = await self.__search_tv(query=query)
            formatted_results = []
            for result in results:
                try:
                    if result["type"] == "series":
                        try:
                            year = result["year"]
                        except KeyError:
                            year = None

                        formatted_results.append(
                            MetaDataProviderSearchResult(
                                poster_images=self.__get_poster_images(
                                    result.get("image_url")
                                ),
                                overview=result.get("overview"),
                                name=result["name"],
                                external_id=result["tvdb_id"],
                                year=year,
                                metadata_provider=self.name,
                                media_type=MediaType.tv,
                                added=False,
                                vote_average=None,
                            )
                        )
                except Exception:
                    log.warning("Error processing search result", exc_info=True)
            return formatted_results
        results = await self.__get_trending_tv()
        formatted_results = []
        for result in results:
            try:
                if result["type"] == "series":
                    try:
                        year = result["year"]
                    except KeyError:
                        year = None

                    formatted_results.append(
                        MetaDataProviderSearchResult(
                            poster_images=self.__get_poster_images(
                                "https://artworks.thetvdb.com" + result.get("image")
                                if result.get("image")
                                else None
                            ),
                            overview=result.get("overview"),
                            name=result["name"],
                            external_id=result["id"],
                            year=year,
                            metadata_provider=self.name,
                            media_type=MediaType.tv,
                            added=False,
                            vote_average=None,
                        )
                    )
            except Exception:
                log.warning("Error processing search result", exc_info=True)
        return formatted_results

    @override
    async def search_movie(
        self, query: str | None = None, max_pages: int = DEFAULT_SEARCH_MAX_PAGES
    ) -> list[MetaDataProviderSearchResult]:
        """
        `max_pages` is accepted for interface parity only: TVDB's search
        returns a single, unpaginated response.
        """
        if query:
            results = await self.__search_movie(query=query)
            results = [r for r in results[0:20] if r["type"] == "movie"]
            log.debug(f"got {len(results)} results from TVDB search")
            movie_payloads = [await self.__get_movie(r["tvdb_id"]) for r in results]
            formatted_results = []
            for result in movie_payloads:
                try:
                    try:
                        year = result["year"]
                    except KeyError:
                        year = None

                    formatted_results.append(
                        MetaDataProviderSearchResult(
                            poster_images=self.__get_poster_images(
                                result.get("image_url")
                            ),
                            overview=result.get("overview"),
                            name=result["name"],
                            external_id=result["tvdb_id"],
                            year=year,
                            metadata_provider=self.name,
                            media_type=MediaType.movie,
                            added=False,
                            vote_average=None,
                        )
                    )
                except Exception:
                    log.warning("Error processing search result", exc_info=True)
            return formatted_results
        results = await self.__get_trending_movies()
        results = results[0:20]
        log.debug(f"got {len(results)} results from TVDB search")
        movie_payloads = [await self.__get_movie(r["id"]) for r in results]
        formatted_results = []
        for result in movie_payloads:
            try:
                try:
                    year = result["year"]
                except KeyError:
                    year = None

                if result.get("image"):
                    poster_path = "https://artworks.thetvdb.com" + str(
                        result.get("image")
                    )
                else:
                    poster_path = None

                formatted_results.append(
                    MetaDataProviderSearchResult(
                        poster_images=self.__get_poster_images(
                            poster_path if result.get("image") else None
                        ),
                        overview=result.get("overview"),
                        name=result["name"],
                        external_id=result["id"],
                        year=year,
                        metadata_provider=self.name,
                        media_type=MediaType.movie,
                        added=False,
                        vote_average=None,
                    )
                )
            except Exception:
                log.warning("Error processing search result", exc_info=True)
        return formatted_results

    @override
    async def search_multi(self, query: str) -> list[MetaDataProviderSearchResult]:
        """
        Search for movies and TV shows together.

        TVDB's search endpoint already returns both types (and more) mixed
        in one response, ranked by TVDB's own relevance - `search_show` and
        `search_movie` each call it too, just to throw away the "other"
        type. Reuse that single call here instead of querying twice.

        Unlike `search_movie`, this does not fetch extended per-movie
        metadata (an extra API call per result), so movie overviews/posters
        may occasionally be missing where the extended lookup would have
        filled them in.
        """
        results = await self.__search_tv(query=query)
        formatted_results = []
        for result in results:
            result_type = result.get("type")
            if result_type not in ("series", "movie"):
                continue
            try:
                try:
                    year = result["year"]
                except KeyError:
                    year = None

                formatted_results.append(
                    MetaDataProviderSearchResult(
                        poster_images=self.__get_poster_images(
                            result.get("image_url")
                        ),
                        overview=result.get("overview"),
                        name=result["name"],
                        external_id=result["tvdb_id"],
                        year=year,
                        metadata_provider=self.name,
                        media_type=MediaType.tv
                        if result_type == "series"
                        else MediaType.movie,
                        added=False,
                        vote_average=None,
                    )
                )
            except Exception:
                log.warning("Error processing search result", exc_info=True)
        return formatted_results

    @override
    async def get_movie_metadata(
        self, movie_id: int, language: str | None = None
    ) -> Movie:
        """

        :param movie_id: the external id of the movie
        :param language: does nothing, TVDB does not support multiple languages
        :return: returns a Movie object
        """
        movie = await self.__get_movie(movie_id=movie_id)

        # get imdb id from remote ids
        imdb_id = None
        remote_ids = movie.get("remoteIds", None)
        if remote_ids:
            for remote_id in remote_ids:
                if remote_id.get("type") == 2:
                    imdb_id = remote_id.get("id")

        return Movie(
            name=movie["name"],
            overview="Overviews are not supported with TVDB",
            year=movie.get("year"),
            external_id=movie["id"],
            metadata_provider=self.name,
            imdb_id=imdb_id,
            metadata_updated_at=datetime.now(UTC),
        )
