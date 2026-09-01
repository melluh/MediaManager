import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import override

import httpx

import media_manager.metadataProvider.utils
from media_manager.common.cache import AsyncTTLCache
from media_manager.config import MediaManagerConfig
from media_manager.metadataProvider.abstract_metadata_provider import (
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
from media_manager.tv.schemas import (
    Episode,
    EpisodeNumber,
    Season,
    SeasonNumber,
    Show,
)

ENDED_STATUS = {"Ended", "Canceled"}
TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p"
TMDB_POSTER_WIDTHS = (92, 154, 185, 342, 500, 780)
TMDB_BACKDROP_WIDTHS = (300, 780, 1280)

# Which metadata JSON key holds each image type's path. Movie and show
# detail payloads use the same key names.
TMDB_IMAGE_METADATA_KEYS: dict[MediaImageType, str] = {
    MediaImageType.poster: "poster_path",
    MediaImageType.backdrop: "backdrop_path",
}

log = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)

_MAX_CONCURRENT_SEASON_FETCHES = 8
"""Caps concurrent per-season TMDB requests when fetching a show - a show can
have an arbitrary number of seasons, so this must not be unbounded."""

# Genre id -> name lookups, lazily populated from a single relay call and
# refreshed periodically since TMDB's genre list can change over time.
GENRE_MAP_MAX_AGE = timedelta(hours=24)
_movie_genre_map: dict[int, str] | None = None
_tv_genre_map: dict[int, str] | None = None
_genre_maps_fetched_at: datetime | None = None
_genre_map_lock = asyncio.Lock()

# These are module-level because TmdbMetadataProvider is instantiated fresh per
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


class TmdbMetadataProvider(AbstractMetadataProvider):
    name = "tmdb"

    def __init__(self) -> None:
        config = MediaManagerConfig().metadata.tmdb
        self.url = config.tmdb_relay_url
        self.primary_languages = config.primary_languages
        self.default_language = config.default_language

    def __get_language_param(self, original_language: str | None) -> str:
        """
        Determine the language parameter to use for TMDB API calls.
        Returns the original language if it's in primary_languages, otherwise returns default_language.

        :param original_language: The original language code (ISO 639-1) of the media
        :return: Language parameter (ISO 639-1 format, e.g., 'en', 'no')
        """
        if original_language and original_language in self.primary_languages:
            return original_language
        return self.default_language

    def __get_poster_images(self, poster_path: str | None) -> list[ExternalPosterImage]:
        if not poster_path:
            return []

        return [
            *[
                ExternalPosterImage(
                    url=f"{TMDB_POSTER_BASE_URL}/w{width}{poster_path}",
                    width=width,
                )
                for width in TMDB_POSTER_WIDTHS
            ],
            ExternalPosterImage(url=f"{TMDB_POSTER_BASE_URL}/original{poster_path}"),
        ]

    def __get_backdrop_images(
        self, backdrop_path: str | None
    ) -> list[ExternalPosterImage]:
        if not backdrop_path:
            return []

        return [
            *[
                ExternalPosterImage(
                    url=f"{TMDB_POSTER_BASE_URL}/w{width}{backdrop_path}",
                    width=width,
                )
                for width in TMDB_BACKDROP_WIDTHS
            ],
            ExternalPosterImage(url=f"{TMDB_POSTER_BASE_URL}/original{backdrop_path}"),
        ]

    async def __cached_get(
        self,
        cache: AsyncTTLCache,
        key: tuple,
        url: str,
        params: dict,
        label: str,
    ) -> dict:
        async def factory() -> dict:
            try:
                response = await _client.get(url=url, params=params, timeout=60)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                log.exception(f"TMDB API error getting {label}")
                if notification_manager.is_configured():
                    await notification_manager.send_notification(
                        title="TMDB API Error",
                        message=f"Failed to fetch {label} from TMDB. Error: {e}",
                    )
                raise

        return await cache.get_or_set(key, factory)

    async def __get_show_metadata(
        self, show_id: int, language: str | None = None
    ) -> dict:
        if language is None:
            language = self.default_language
        return await self.__cached_get(
            _detail_cache,
            ("show_meta", show_id, language),
            url=f"{self.url}/tv/shows/{show_id}",
            params={"language": language},
            label=f"show metadata for ID {show_id}",
        )

    async def __get_season_metadata(
        self, show_id: int, season_number: int, language: str | None = None
    ) -> dict:
        if language is None:
            language = self.default_language
        return await self.__cached_get(
            _season_cache,
            ("season", show_id, season_number, language),
            url=f"{self.url}/tv/shows/{show_id}/{season_number}",
            params={"language": language},
            label=f"season {season_number} metadata for show ID {show_id}",
        )

    async def __search_tv(self, query: str, page: int) -> dict:
        try:
            response = await _client.get(
                url=f"{self.url}/tv/search",
                params={
                    "query": query,
                    "page": page,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TMDB API error searching TV shows with query '{query}'")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to search TV shows with query '{query}' on TMDB. Error: {e}",
                )
            raise

    async def __get_trending_tv(self) -> dict:
        return await self.__cached_get(
            _trending_cache,
            ("trending_tv", self.default_language),
            url=f"{self.url}/tv/trending",
            params={"language": self.default_language},
            label="trending TV shows",
        )

    async def __get_movie_metadata(
        self, movie_id: int, language: str | None = None
    ) -> dict:
        if language is None:
            language = self.default_language
        return await self.__cached_get(
            _detail_cache,
            ("movie_meta", movie_id, language),
            url=f"{self.url}/movies/{movie_id}",
            params={"language": language},
            label=f"movie metadata for ID {movie_id}",
        )

    async def __search_movie(self, query: str, page: int) -> dict:
        try:
            response = await _client.get(
                url=f"{self.url}/movies/search",
                params={
                    "query": query,
                    "page": page,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TMDB API error searching movies with query '{query}'")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to search movies with query '{query}' on TMDB. Error: {e}",
                )
            raise

    async def __search_multi(self, query: str, page: int) -> dict:
        try:
            response = await _client.get(
                url=f"{self.url}/search/multi",
                params={
                    "query": query,
                    "page": page,
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TMDB API error searching multi with query '{query}'")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to search multi with query '{query}' on TMDB. Error: {e}",
                )
            raise

    async def __get_trending_movies(self) -> dict:
        return await self.__cached_get(
            _trending_cache,
            ("trending_movies", self.default_language),
            url=f"{self.url}/movies/trending",
            params={"language": self.default_language},
            label="trending movies",
        )

    async def __refresh_genre_maps_if_stale(self) -> None:
        global _movie_genre_map, _tv_genre_map, _genre_maps_fetched_at

        def is_stale() -> bool:
            return (
                _genre_maps_fetched_at is None
                or datetime.now(UTC) - _genre_maps_fetched_at
                > GENRE_MAP_MAX_AGE
            )

        if not is_stale():
            return
        async with _genre_map_lock:
            if not is_stale():
                return
            try:
                response = await _client.get(
                    url=f"{self.url}/genres",
                    params={"language": self.default_language},
                    timeout=30,
                )
                response.raise_for_status()
                data = response.json()
                _movie_genre_map = {
                    genre["id"]: genre["name"] for genre in data.get("movie", [])
                }
                _tv_genre_map = {
                    genre["id"]: genre["name"] for genre in data.get("tv", [])
                }
                _genre_maps_fetched_at = datetime.now(UTC)
            except httpx.HTTPError:
                log.warning("Failed to fetch TMDB genre lists", exc_info=True)

    async def __get_movie_genre_map(self) -> dict[int, str]:
        await self.__refresh_genre_maps_if_stale()
        return _movie_genre_map or {}

    async def __get_tv_genre_map(self) -> dict[int, str]:
        await self.__refresh_genre_maps_if_stale()
        return _tv_genre_map or {}

    async def __get_media_metadata(
        self, media: Movie | Show, media_type: MediaType, language: str
    ) -> dict:
        if media_type == MediaType.tv:
            return await self.__get_show_metadata(media.external_id, language=language)
        return await self.__get_movie_metadata(
            movie_id=media.external_id, language=language
        )

    @override
    async def get_available_image_types(
        self, media: Movie | Show, media_type: MediaType
    ) -> set[MediaImageType]:
        language = self.__get_language_param(media.original_language)
        metadata = await self.__get_media_metadata(media, media_type, language)
        return {
            image_type
            for image_type, metadata_key in TMDB_IMAGE_METADATA_KEYS.items()
            if metadata.get(metadata_key) is not None
        }

    @override
    async def download_media_image(
        self, media: Movie | Show, media_type: MediaType, image_type: MediaImageType
    ) -> bool:
        # Determine which language to use based on the media's original_language
        language = self.__get_language_param(media.original_language)

        # Fetch metadata in the appropriate language to get a localized image
        metadata = await self.__get_media_metadata(media, media_type, language)

        image_path = metadata.get(TMDB_IMAGE_METADATA_KEYS[image_type])
        if image_path is None:
            log.warning(
                f"{image_type} image for {media_type} {media.name} could not be downloaded"
            )
            return False

        # all images from TMDB should already be jpeg, so no need to convert
        image_url = f"{TMDB_POSTER_BASE_URL}/original{image_path}"
        if await media_manager.metadataProvider.utils.download_media_image(
            storage_path=self.storage_path,
            image_url=image_url,
            media_id=media.id,
            image_type=image_type,
        ):
            log.info(
                f"Successfully downloaded {image_type} image for {media_type} {media.name}"
            )
            return True
        log.warning(f"download for {image_type} image of {media_type} {media.name} failed")
        return False

    @override
    async def get_available_season_image_types(
        self, show: Show, season: Season
    ) -> set[MediaImageType]:
        language = self.__get_language_param(show.original_language)
        season_metadata = await self.__get_season_metadata(
            show_id=show.external_id, season_number=season.number, language=language
        )
        return {MediaImageType.poster} if season_metadata.get("poster_path") else set()

    @override
    async def download_season_image(
        self, show: Show, season: Season, image_type: MediaImageType
    ) -> bool:
        if image_type is not MediaImageType.poster:
            log.debug(f"{image_type} images are not supported for TMDB seasons")
            return False

        language = self.__get_language_param(show.original_language)
        season_metadata = await self.__get_season_metadata(
            show_id=show.external_id, season_number=season.number, language=language
        )

        poster_path = season_metadata.get("poster_path")
        if poster_path is None:
            log.warning(
                f"poster image for {show.name} season {season.number} could not be downloaded"
            )
            return False

        image_url = f"{TMDB_POSTER_BASE_URL}/original{poster_path}"
        if await media_manager.metadataProvider.utils.download_media_image(
            storage_path=self.storage_path,
            image_url=image_url,
            media_id=season.id,
            image_type=MediaImageType.poster,
        ):
            log.info(
                f"Successfully downloaded poster image for {show.name} season {season.number}"
            )
            return True
        log.warning(
            f"download for poster image of {show.name} season {season.number} failed"
        )
        return False

    @override
    async def get_show_metadata(
        self, show_id: int, language: str | None = None
    ) -> Show:
        """

        :param show_id: the external id of the show
        :type show_id: int
        :param language: optional language code (ISO 639-1) to fetch metadata in
        :type language: str | None
        :return: returns a Show object
        :rtype: Show
        """
        # If language not provided, fetch once to determine original language
        if language is None:
            show_metadata = await self.__get_show_metadata(show_id)
            language = show_metadata.get("original_language")

        # Determine which language to use for metadata
        language = self.__get_language_param(language)

        # Fetch show metadata in the appropriate language
        show_metadata = await self.__get_show_metadata(show_id, language=language)

        imdb_id = show_metadata.get("external_ids", {}).get("imdb_id")
        trailer_url = self.__get_first_trailer(show_metadata.get("videos", {"results": []}).get("results", []))

        season_fetch_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_SEASON_FETCHES)

        async def _fetch_season(season_number: int) -> dict:
            async with season_fetch_semaphore:
                return await self.__get_season_metadata(
                    show_id=show_metadata["id"],
                    season_number=season_number,
                    language=language,
                )

        season_metadata_list = await asyncio.gather(
            *(
                _fetch_season(season["season_number"])
                for season in show_metadata["seasons"]
            )
        )
        season_list = [
            Season(
                external_id=int(season_metadata["id"]),
                name=season_metadata["name"],
                overview=season_metadata["overview"],
                number=SeasonNumber(season_metadata["season_number"]),
                episodes=[
                    Episode(
                        external_id=int(episode["id"]),
                        title=episode["name"],
                        number=EpisodeNumber(episode["episode_number"]),
                    )
                    for episode in season_metadata["episodes"]
                ],
            )
            for season_metadata in season_metadata_list
        ]

        year = media_manager.metadataProvider.utils.get_year_from_date(
            show_metadata["first_air_date"]
        )

        episode_run_times = show_metadata.get("episode_run_time") or []

        return Show(
            external_id=show_id,
            name=show_metadata["name"],
            overview=show_metadata["overview"],
            year=year,
            seasons=season_list,
            metadata_provider=self.name,
            ended=show_metadata["status"] in ENDED_STATUS,
            original_language=show_metadata.get("original_language"),
            imdb_id=imdb_id,
            trailer_url=trailer_url,
            tagline=show_metadata.get("tagline") or None,
            genres=media_manager.metadataProvider.utils.get_genre_names(
                show_metadata.get("genres")
            ),
            runtime=episode_run_times[0] if episode_run_times else None,
            release_date=show_metadata.get("first_air_date") or None,
            metadata_updated_at=datetime.now(UTC),
        )

    @override
    async def search_show(
        self, query: str | None = None, max_pages: int = 5
    ) -> list[MetaDataProviderSearchResult]:
        """
        Search for shows using TMDB API.
        If no query is provided, it will return the most popular shows.
        """
        results = []
        if query is None:
            results = (await self.__get_trending_tv())["results"]
        else:
            for page_number in range(1, max_pages + 1):
                result_page = await self.__search_tv(query=query, page=page_number)

                if not result_page["results"]:
                    break
                results.extend(result_page["results"])

        tv_genre_map = await self.__get_tv_genre_map()

        formatted_results = []
        for result in results:
            try:
                # Determine which name to use based on primary_languages
                original_language = result.get("original_language")
                original_name = result.get("original_name")
                display_name = result["name"]

                overview = result["overview"]
                # Use original name if language is in primary_languages and skip overview
                if original_language and original_language in self.primary_languages:
                    display_name = original_name
                    overview = None

                formatted_results.append(
                    MetaDataProviderSearchResult(
                        poster_images=self.__get_poster_images(result.get("poster_path")),
                        backdrop_images=self.__get_backdrop_images(
                            result.get("backdrop_path")
                        ),
                        overview=overview,
                        name=display_name,
                        external_id=result["id"],
                        year=media_manager.metadataProvider.utils.get_year_from_date(
                            result["first_air_date"]
                        ),
                        metadata_provider=self.name,
                        media_type=MediaType.tv,
                        added=False,
                        vote_average=result["vote_average"],
                        original_language=original_language,
                        genres=media_manager.metadataProvider.utils.get_genre_names_from_ids(
                            result.get("genre_ids"), tv_genre_map
                        ),
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
        Get movie metadata with language-aware fetching.

        :param movie_id: the external id of the movie
        :type movie_id: int
        :param language: optional language code (ISO 639-1) to fetch metadata in
        :type language: str | None
        :return: returns a Movie object
        :rtype: Movie
        """
        # If language not provided, fetch once to determine original language
        if language is None:
            movie_metadata = await self.__get_movie_metadata(movie_id=movie_id)
            language = movie_metadata.get("original_language")

        # Determine which language to use for metadata
        language = self.__get_language_param(language)

        # Fetch movie metadata in the appropriate language
        movie_metadata = await self.__get_movie_metadata(
            movie_id=movie_id, language=language
        )

        imdb_id = movie_metadata.get("external_ids", {}).get("imdb_id")
        trailer_url = self.__get_first_trailer(movie_metadata.get("videos", {"results": []}).get("results", []))

        year = media_manager.metadataProvider.utils.get_year_from_date(
            movie_metadata["release_date"]
        )

        return Movie(
            external_id=movie_id,
            name=movie_metadata["title"],
            overview=movie_metadata["overview"],
            year=year,
            metadata_provider=self.name,
            original_language=movie_metadata.get("original_language"),
            imdb_id=imdb_id,
            trailer_url=trailer_url,
            tagline=movie_metadata.get("tagline") or None,
            genres=media_manager.metadataProvider.utils.get_genre_names(
                movie_metadata.get("genres")
            ),
            runtime=movie_metadata.get("runtime"),
            release_date=movie_metadata.get("release_date") or None,
            metadata_updated_at=datetime.now(UTC),
        )

    @override
    async def search_movie(
        self, query: str | None = None, max_pages: int = 5
    ) -> list[MetaDataProviderSearchResult]:
        """
        Search for movies using TMDB API.
        If no query is provided, it will return the most popular movies.
        """
        results = []
        if query is None:
            results = (await self.__get_trending_movies())["results"]
        else:
            for page_number in range(1, max_pages + 1):
                result_page = await self.__search_movie(query=query, page=page_number)

                if not result_page["results"]:
                    break
                results.extend(result_page["results"])

        movie_genre_map = await self.__get_movie_genre_map()

        formatted_results = []
        for result in results:
            try:
                # Determine which name to use based on primary_languages
                original_language = result.get("original_language")
                original_title = result.get("original_title")
                display_name = result["title"]

                overview = result["overview"]
                # Use original name if language is in primary_languages and skip overview
                if original_language and original_language in self.primary_languages:
                    display_name = original_title
                    overview = None

                formatted_results.append(
                    MetaDataProviderSearchResult(
                        poster_images=self.__get_poster_images(result.get("poster_path")),
                        backdrop_images=self.__get_backdrop_images(
                            result.get("backdrop_path")
                        ),
                        overview=overview,
                        name=display_name,
                        external_id=result["id"],
                        year=media_manager.metadataProvider.utils.get_year_from_date(
                            result["release_date"]
                        ),
                        metadata_provider=self.name,
                        media_type=MediaType.movie,
                        added=False,
                        vote_average=result["vote_average"],
                        original_language=original_language,
                        genres=media_manager.metadataProvider.utils.get_genre_names_from_ids(
                            result.get("genre_ids"), movie_genre_map
                        ),
                    )
                )
            except Exception:
                log.warning("Error processing search result", exc_info=True)

        return formatted_results

    @override
    async def search_multi(
        self, query: str, max_pages: int = 5
    ) -> list[MetaDataProviderSearchResult]:
        """
        Search for movies and TV shows together using TMDB's combined
        search, so results are ranked the same way as on TMDB's own website
        instead of stitching two separately-ranked lists together.
        """
        results = []
        for page_number in range(1, max_pages + 1):
            result_page = await self.__search_multi(query=query, page=page_number)

            if not result_page["results"]:
                break
            results.extend(result_page["results"])

        movie_genre_map = await self.__get_movie_genre_map()
        tv_genre_map = await self.__get_tv_genre_map()

        formatted_results = []
        for result in results:
            media_type = result.get("media_type")
            if media_type not in ("movie", "tv"):
                continue
            try:
                if media_type == "movie":
                    original_name = result.get("original_title")
                    display_name = result["title"]
                    release_date = result.get("release_date")
                    genre_map = movie_genre_map
                else:
                    original_name = result.get("original_name")
                    display_name = result["name"]
                    release_date = result.get("first_air_date")
                    genre_map = tv_genre_map

                # Determine which name to use based on primary_languages
                original_language = result.get("original_language")
                overview = result.get("overview")
                if original_language and original_language in self.primary_languages:
                    display_name = original_name
                    overview = None

                formatted_results.append(
                    MetaDataProviderSearchResult(
                        poster_images=self.__get_poster_images(result.get("poster_path")),
                        backdrop_images=self.__get_backdrop_images(
                            result.get("backdrop_path")
                        ),
                        overview=overview,
                        name=display_name,
                        external_id=result["id"],
                        year=media_manager.metadataProvider.utils.get_year_from_date(
                            release_date
                        ),
                        metadata_provider=self.name,
                        media_type=MediaType.movie
                        if media_type == "movie"
                        else MediaType.tv,
                        added=False,
                        vote_average=result.get("vote_average"),
                        original_language=original_language,
                        genres=media_manager.metadataProvider.utils.get_genre_names_from_ids(
                            result.get("genre_ids"), genre_map
                        ),
                    )
                )
            except Exception:
                log.warning("Error processing search result", exc_info=True)
        return formatted_results

    def __get_first_trailer(self, videos: list[dict]) -> str | None:
        for video in videos:
            if video["type"] == "Trailer":
                url = self.__get_video_url(video["site"], video["key"])
                if not url:
                    continue
                return url
        return None

    def __get_video_url(self, site: str, key: str) -> str | None:
        if site == "YouTube":
            return f"https://www.youtube.com/watch?v={key}"
        return None
