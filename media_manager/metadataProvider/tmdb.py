import asyncio
import logging
from datetime import datetime, timezone
from typing import override

import httpx

import media_manager.metadataProvider.utils
from media_manager.config import MediaManagerConfig
from media_manager.metadataProvider.abstract_metadata_provider import (
    AbstractMetadataProvider,
)
from media_manager.metadataProvider.schemas import (
    ExternalPosterImage,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.schemas import Movie
from media_manager.notification.manager import notification_manager
from media_manager.tv.schemas import Episode, EpisodeNumber, Season, SeasonNumber, Show

ENDED_STATUS = {"Ended", "Canceled"}
TMDB_POSTER_BASE_URL = "https://image.tmdb.org/t/p"
TMDB_POSTER_WIDTHS = (92, 154, 185, 342, 500, 780)

log = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)

# Genre id -> name lookup, lazily populated and cached for the process
# lifetime since TMDB's genre list is effectively static.
_movie_genre_map: dict[int, str] | None = None
_tv_genre_map: dict[int, str] | None = None
_genre_map_lock = asyncio.Lock()

# Popular/trending results are enriched with an extra per-item detail call
# (to get runtime, which trending/search responses don't include). Bound
# the concurrency so a dashboard load doesn't fire ~20 simultaneous requests
# at TMDB.
_detail_semaphore = asyncio.Semaphore(5)


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

    async def __get_show_metadata(
        self, show_id: int, language: str | None = None
    ) -> dict:
        if language is None:
            language = self.default_language
        try:
            response = await _client.get(
                url=f"{self.url}/tv/shows/{show_id}",
                params={"language": language},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TMDB API error getting show metadata for ID {show_id}")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to fetch show metadata for ID {show_id} from TMDB. Error: {e}",
                )
            raise

    async def __get_show_external_ids(self, show_id: int) -> dict:
        try:
            response = await _client.get(
                url=f"{self.url}/tv/shows/{show_id}/external_ids",
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TMDB API error getting show external IDs for ID {show_id}")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to fetch show external IDs for ID {show_id} from TMDB. Error: {e}",
                )
            raise

    async def __get_season_metadata(
        self, show_id: int, season_number: int, language: str | None = None
    ) -> dict:
        if language is None:
            language = self.default_language
        try:
            response = await _client.get(
                url=f"{self.url}/tv/shows/{show_id}/{season_number}",
                params={"language": language},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(
                f"TMDB API error getting season {season_number} metadata for show ID {show_id}"
            )
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to fetch season {season_number} metadata for show ID {show_id} from TMDB. Error: {e}",
                )
            raise

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
        try:
            response = await _client.get(
                url=f"{self.url}/tv/trending",
                params={"language": self.default_language},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception("TMDB API error getting trending TV")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to fetch trending TV shows from TMDB. Error: {e}",
                )
            raise

    async def __get_movie_metadata(
        self, movie_id: int, language: str | None = None
    ) -> dict:
        if language is None:
            language = self.default_language
        try:
            response = await _client.get(
                url=f"{self.url}/movies/{movie_id}",
                params={"language": language},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(f"TMDB API error getting movie metadata for ID {movie_id}")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to fetch movie metadata for ID {movie_id} from TMDB. Error: {e}",
                )
            raise

    async def __get_movie_external_ids(self, movie_id: int) -> dict:
        try:
            response = await _client.get(
                url=f"{self.url}/movies/{movie_id}/external_ids", timeout=60
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception(
                f"TMDB API error getting movie external IDs for ID {movie_id}"
            )
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to fetch movie external IDs for ID {movie_id} from TMDB. Error: {e}",
                )
            raise

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
        try:
            response = await _client.get(
                url=f"{self.url}/movies/trending",
                params={"language": self.default_language},
                timeout=60,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            log.exception("TMDB API error getting trending movies")
            if notification_manager.is_configured():
                await notification_manager.send_notification(
                    title="TMDB API Error",
                    message=f"Failed to fetch trending movies from TMDB. Error: {e}",
                )
            raise

    async def __get_movie_genre_map(self) -> dict[int, str]:
        global _movie_genre_map
        if _movie_genre_map is None:
            async with _genre_map_lock:
                if _movie_genre_map is None:
                    try:
                        response = await _client.get(
                            url=f"{self.url}/genre/movie/list",
                            params={"language": self.default_language},
                            timeout=30,
                        )
                        response.raise_for_status()
                        _movie_genre_map = {
                            genre["id"]: genre["name"]
                            for genre in response.json().get("genres", [])
                        }
                    except httpx.HTTPError:
                        log.warning("Failed to fetch TMDB movie genre list", exc_info=True)
                        return {}
        return _movie_genre_map

    async def __get_tv_genre_map(self) -> dict[int, str]:
        global _tv_genre_map
        if _tv_genre_map is None:
            async with _genre_map_lock:
                if _tv_genre_map is None:
                    try:
                        response = await _client.get(
                            url=f"{self.url}/genre/tv/list",
                            params={"language": self.default_language},
                            timeout=30,
                        )
                        response.raise_for_status()
                        _tv_genre_map = {
                            genre["id"]: genre["name"]
                            for genre in response.json().get("genres", [])
                        }
                    except httpx.HTTPError:
                        log.warning("Failed to fetch TMDB TV genre list", exc_info=True)
                        return {}
        return _tv_genre_map

    async def __enrich_shows_with_details(
        self, results: list[MetaDataProviderSearchResult]
    ) -> None:
        """
        Trending/popular shows don't come with runtime, and only carry
        genre ids rather than names. Fill both in from the per-show detail
        endpoint, bounded by `_detail_semaphore` to avoid hammering TMDB.
        """

        async def enrich(result: MetaDataProviderSearchResult) -> None:
            try:
                async with _detail_semaphore:
                    metadata = await self.__get_show_metadata(
                        show_id=result.external_id, language=self.default_language
                    )
                result.genres = media_manager.metadataProvider.utils.get_genre_names(
                    metadata.get("genres")
                )
                episode_run_times = metadata.get("episode_run_time") or []
                result.runtime = episode_run_times[0] if episode_run_times else None
            except Exception:
                log.warning(
                    f"Failed to fetch extra details for show {result.external_id}",
                    exc_info=True,
                )

        await asyncio.gather(*(enrich(result) for result in results))

    async def __enrich_movies_with_details(
        self, results: list[MetaDataProviderSearchResult]
    ) -> None:
        """
        Same as `__enrich_shows_with_details`, for movies.
        """

        async def enrich(result: MetaDataProviderSearchResult) -> None:
            try:
                async with _detail_semaphore:
                    metadata = await self.__get_movie_metadata(
                        movie_id=result.external_id, language=self.default_language
                    )
                result.genres = media_manager.metadataProvider.utils.get_genre_names(
                    metadata.get("genres")
                )
                result.runtime = metadata.get("runtime")
            except Exception:
                log.warning(
                    f"Failed to fetch extra details for movie {result.external_id}",
                    exc_info=True,
                )

        await asyncio.gather(*(enrich(result) for result in results))

    @override
    async def download_show_poster_image(self, show: Show) -> bool:
        # Determine which language to use based on show's original_language
        language = self.__get_language_param(show.original_language)

        # Fetch metadata in the appropriate language to get localized poster
        show_metadata = await self.__get_show_metadata(
            show.external_id, language=language
        )

        # downloading the poster
        # all pictures from TMDB should already be jpeg, so no need to convert
        if show_metadata["poster_path"] is not None:
            poster_url = (
                "https://image.tmdb.org/t/p/original" + show_metadata["poster_path"]
            )
            if await media_manager.metadataProvider.utils.download_poster_image(
                storage_path=self.storage_path, poster_url=poster_url, uuid=show.id
            ):
                log.info("Successfully downloaded poster image for show " + show.name)
            else:
                log.warning(f"download for image of show {show.name} failed")
                return False
        else:
            log.warning(f"image for show {show.name} could not be downloaded")
            return False
        return True

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

        # get imdb id
        external_ids = await self.__get_show_external_ids(show_id=show_id)
        imdb_id = external_ids.get("imdb_id")

        season_metadata_list = [
            await self.__get_season_metadata(
                show_id=show_metadata["id"],
                season_number=season["season_number"],
                language=language,
            )
            for season in show_metadata["seasons"]
        ]
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
            tagline=show_metadata.get("tagline") or None,
            genres=media_manager.metadataProvider.utils.get_genre_names(
                show_metadata.get("genres")
            ),
            runtime=episode_run_times[0] if episode_run_times else None,
            release_date=show_metadata.get("first_air_date") or None,
            metadata_updated_at=datetime.now(timezone.utc),
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
        is_popular = query is None
        if is_popular:
            results = (await self.__get_trending_tv())["results"]
        else:
            for page_number in range(1, max_pages + 1):
                result_page = await self.__search_tv(query=query, page=page_number)

                if not result_page["results"]:
                    break
                results.extend(result_page["results"])

        tv_genre_map = {} if is_popular else await self.__get_tv_genre_map()

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

        if is_popular:
            await self.__enrich_shows_with_details(formatted_results)

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

        # get imdb id
        external_ids = await self.__get_movie_external_ids(movie_id=movie_id)
        imdb_id = external_ids.get("imdb_id")

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
            tagline=movie_metadata.get("tagline") or None,
            genres=media_manager.metadataProvider.utils.get_genre_names(
                movie_metadata.get("genres")
            ),
            runtime=movie_metadata.get("runtime"),
            release_date=movie_metadata.get("release_date") or None,
            metadata_updated_at=datetime.now(timezone.utc),
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
        is_popular = query is None
        if is_popular:
            results = (await self.__get_trending_movies())["results"]
        else:
            for page_number in range(1, max_pages + 1):
                result_page = await self.__search_movie(query=query, page=page_number)

                if not result_page["results"]:
                    break
                results.extend(result_page["results"])

        movie_genre_map = {} if is_popular else await self.__get_movie_genre_map()

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

        if is_popular:
            await self.__enrich_movies_with_details(formatted_results)

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

    @override
    async def download_movie_poster_image(self, movie: Movie) -> bool:
        # Determine which language to use based on movie's original_language
        language = self.__get_language_param(movie.original_language)

        # Fetch metadata in the appropriate language to get localized poster
        movie_metadata = await self.__get_movie_metadata(
            movie_id=movie.external_id, language=language
        )

        # downloading the poster
        # all pictures from TMDB should already be jpeg, so no need to convert
        if movie_metadata["poster_path"] is not None:
            poster_url = (
                "https://image.tmdb.org/t/p/original" + movie_metadata["poster_path"]
            )
            if await media_manager.metadataProvider.utils.download_poster_image(
                storage_path=self.storage_path, poster_url=poster_url, uuid=movie.id
            ):
                log.info("Successfully downloaded poster image for movie " + movie.name)
            else:
                log.warning(f"download for image of movie {movie.name} failed")
                return False
        else:
            log.warning(f"image for movie {movie.name} could not be downloaded")
            return False
        return True
