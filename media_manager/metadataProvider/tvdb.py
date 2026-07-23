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
from media_manager.tv.schemas import Episode, Season, SeasonNumber, Show

log = logging.getLogger(__name__)

_client = httpx.AsyncClient(timeout=30.0)


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

    async def __get_show(self, show_id: int) -> dict:
        response = await _client.get(url=f"{self.url}/tv/shows/{show_id}", timeout=60)
        return response.json()

    async def __get_season(self, show_id: int) -> dict:
        response = await _client.get(
            url=f"{self.url}/tv/seasons/{show_id}", timeout=60
        )
        return response.json()

    async def __search_tv(self, query: str) -> dict:
        response = await _client.get(
            url=f"{self.url}/tv/search", params={"query": query}, timeout=60
        )
        return response.json()

    async def __get_trending_tv(self) -> dict:
        response = await _client.get(url=f"{self.url}/tv/trending", timeout=60)
        return response.json()

    async def __get_movie(self, movie_id: int) -> dict:
        response = await _client.get(url=f"{self.url}/movies/{movie_id}", timeout=60)
        return response.json()

    async def __search_movie(self, query: str) -> dict:
        response = await _client.get(
            url=f"{self.url}/movies/search", params={"query": query}, timeout=60
        )
        return response.json()

    async def __get_trending_movies(self) -> dict:
        response = await _client.get(url=f"{self.url}/movies/trending", timeout=60)
        return response.json()

    @override
    async def download_show_poster_image(self, show: Show) -> bool:
        show_metadata = await self.__get_show(show_id=show.external_id)

        if show_metadata["image"] is not None:
            await media_manager.metadataProvider.utils.download_poster_image(
                storage_path=self.storage_path,
                poster_url=show_metadata["image"],
                uuid=show.id,
            )
            log.debug("Successfully downloaded poster image for show " + show.name)
            return True
        log.warning(f"image for show {show.name} could not be downloaded")
        return False

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

        season_payloads = [await self.__get_season(show_id=sid) for sid in seasons_ids]
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
            metadata_updated_at=datetime.now(timezone.utc),
        )

    @override
    async def search_show(
        self, query: str | None = None
    ) -> list[MetaDataProviderSearchResult]:
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
        self, query: str | None = None
    ) -> list[MetaDataProviderSearchResult]:
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
    async def download_movie_poster_image(self, movie: Movie) -> bool:
        movie_metadata = await self.__get_movie(movie.external_id)

        if movie_metadata["image"] is not None:
            await media_manager.metadataProvider.utils.download_poster_image(
                storage_path=self.storage_path,
                poster_url=movie_metadata["image"],
                uuid=movie.id,
            )
            log.info("Successfully downloaded poster image for show " + movie.name)
            return True
        log.warning(f"image for show {movie.name} could not be downloaded")
        return False

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
            metadata_updated_at=datetime.now(timezone.utc),
        )
