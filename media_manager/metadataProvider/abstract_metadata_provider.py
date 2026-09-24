import asyncio
import logging
from abc import ABC, abstractmethod

from media_manager.config import MediaManagerConfig
from media_manager.metadataProvider.schemas import (
    ExternalPosterImage,
    MediaImageType,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.schemas import Movie
from media_manager.tv.schemas import Season, SeasonId, Show

log = logging.getLogger(__name__)

DEFAULT_SEARCH_MAX_PAGES = 5
"""Pages fetched by an interactive search, where a deep result list is worth
the extra requests."""

_MAX_CONCURRENT_IMAGE_DOWNLOADS = 8
"""Caps concurrent image downloads per add/update - a show can have an
arbitrary number of seasons, so this must not be unbounded."""


class AbstractMetadataProvider(ABC):
    storage_path = MediaManagerConfig().misc.image_directory

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def get_show_metadata(
        self, show_id: int, language: str | None = None
    ) -> Show:
        raise NotImplementedError()

    @abstractmethod
    async def get_movie_metadata(
        self, movie_id: int, language: str | None = None
    ) -> Movie:
        raise NotImplementedError()

    @abstractmethod
    async def get_show_images(
        self, show_id: int
    ) -> tuple[list[ExternalPosterImage], list[ExternalPosterImage]]:
        """
        Poster and backdrop images for a show, resolved by id rather than by
        search - used to illustrate a match found via an id already known
        (e.g. one embedded in a directory name), without a full detail fetch.

        :return: (poster_images, backdrop_images)
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_movie_images(
        self, movie_id: int
    ) -> tuple[list[ExternalPosterImage], list[ExternalPosterImage]]:
        """
        Poster and backdrop images for a movie, resolved by id. See
        `get_show_images`.

        :return: (poster_images, backdrop_images)
        """
        raise NotImplementedError()

    @abstractmethod
    async def search_show(
        self, query: str | None = None, max_pages: int = DEFAULT_SEARCH_MAX_PAGES
    ) -> list[MetaDataProviderSearchResult]:
        """
        :param max_pages: How many pages of results to fetch, for providers
            that paginate. Each page is one request, so callers that only need
            the top results (the import scan) should ask for one.
        """
        raise NotImplementedError()

    @abstractmethod
    async def search_movie(
        self, query: str | None = None, max_pages: int = DEFAULT_SEARCH_MAX_PAGES
    ) -> list[MetaDataProviderSearchResult]:
        """
        :param max_pages: How many pages of results to fetch, for providers
            that paginate. Each page is one request, so callers that only need
            the top results (the import scan) should ask for one.
        """
        raise NotImplementedError()

    @abstractmethod
    async def search_multi(self, query: str) -> list[MetaDataProviderSearchResult]:
        """
        Search for movies and TV shows together, ranked the way the
        provider itself ranks combined results (e.g. TMDB's own website).
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_available_image_types(
        self, media: Movie | Show, media_type: MediaType
    ) -> set[MediaImageType]:
        """
        Which image types (poster, backdrop, ...) this provider currently
        has available for the given media item.
        """
        raise NotImplementedError()

    @abstractmethod
    async def download_media_image(
        self, media: Movie | Show, media_type: MediaType, image_type: MediaImageType
    ) -> str | None:
        """
        Downloads a single image for a movie or show, skipping the fetch if
        the provider's resolved path/URL for it already matches
        `media.image_source_paths[image_type]` and the file is still on
        disk.

        :param media: The movie or show to download the image for.
        :param media_type: Whether `media` is a movie or a show.
        :param image_type: Which image (poster, backdrop, ...) to download.
        :return: The provider path/URL the image is now current with (freshly
            downloaded or already up to date), or None if unavailable/failed.
        """
        raise NotImplementedError()

    async def download_all_media_images(
        self, media: Movie | Show, media_type: MediaType
    ) -> dict[MediaImageType, str]:
        """
        Downloads every image type this provider has available for the
        given media item. Does not touch season images - callers with a
        `Show` should also call `download_all_season_images` for those.

        :return: image_type -> resolved provider path/URL, for every image
            type that's now current (freshly downloaded or already up to
            date) - for callers to persist via `upsert_media_image_source`.
        """
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_IMAGE_DOWNLOADS)

        async def _download(
            image_type: MediaImageType,
        ) -> tuple[MediaImageType, str | None]:
            async with semaphore:
                return image_type, await self.download_media_image(
                    media, media_type, image_type
                )

        image_types = await self.get_available_image_types(media, media_type)
        results = await asyncio.gather(*(_download(t) for t in image_types))
        return {
            image_type: source_path
            for image_type, source_path in results
            if source_path is not None
        }

    @abstractmethod
    async def get_available_season_image_types(
        self, show: Show, season: Season
    ) -> set[MediaImageType]:
        """
        Which image types this provider currently has available for the
        given season. In practice only `poster` is ever returned - seasons
        don't have their own backdrop art.
        """
        raise NotImplementedError()

    @abstractmethod
    async def download_season_image(
        self, show: Show, season: Season, image_type: MediaImageType
    ) -> str | None:
        """
        Downloads a single image for a season, keyed on disk by the
        season's own id (same layout `download_media_image` uses for a
        movie/show, keyed by `media.id`), skipping the fetch under the same
        conditions `download_media_image` does.

        :return: The provider path/URL the image is now current with, or
            None if unavailable/failed.
        """
        raise NotImplementedError()

    async def download_all_season_images(self, show: Show) -> dict[SeasonId, str]:
        """
        Downloads every image type available for every season of the show.

        :return: season id -> resolved poster path/URL, for every season
            whose poster is now current - for callers to persist via
            `upsert_media_image_source`.
        """
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_IMAGE_DOWNLOADS)

        async def _download_season(season: Season) -> tuple[SeasonId, str | None]:
            resolved: str | None = None
            for image_type in await self.get_available_season_image_types(show, season):
                async with semaphore:
                    resolved = await self.download_season_image(show, season, image_type)
            return season.id, resolved

        results = await asyncio.gather(
            *(_download_season(season) for season in show.seasons)
        )
        return {
            season_id: source_path
            for season_id, source_path in results
            if source_path is not None
        }
