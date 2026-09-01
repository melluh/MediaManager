import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Coroutine
from typing import Any

from media_manager.config import MediaManagerConfig
from media_manager.metadataProvider.schemas import (
    MediaImageType,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.schemas import Movie
from media_manager.tv.schemas import Season, Show

log = logging.getLogger(__name__)

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
    async def search_show(
        self, query: str | None = None
    ) -> list[MetaDataProviderSearchResult]:
        raise NotImplementedError()

    @abstractmethod
    async def search_movie(
        self, query: str | None = None
    ) -> list[MetaDataProviderSearchResult]:
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
    ) -> bool:
        """
        Downloads a single image for a movie or show.
        :param media: The movie or show to download the image for.
        :param media_type: Whether `media` is a movie or a show.
        :param image_type: Which image (poster, backdrop, ...) to download.
        :return: True if the image was downloaded successfully, False otherwise.
        """
        raise NotImplementedError()

    async def download_all_media_images(
        self, media: Movie | Show, media_type: MediaType
    ) -> None:
        """
        Downloads every image type this provider has available for the
        given media item (and, for shows, every season's poster too).
        """
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_IMAGE_DOWNLOADS)

        async def _download(image_type: MediaImageType) -> bool:
            async with semaphore:
                return await self.download_media_image(media, media_type, image_type)

        image_types = await self.get_available_image_types(media, media_type)
        tasks: list[Coroutine[Any, Any, Any]] = [
            _download(image_type) for image_type in image_types
        ]
        if isinstance(media, Show):
            tasks.append(self.download_all_season_images(media))
        await asyncio.gather(*tasks)

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
    ) -> bool:
        """
        Downloads a single image for a season, keyed on disk by the
        season's own id (same layout `download_media_image` uses for a
        movie/show, keyed by `media.id`).
        """
        raise NotImplementedError()

    async def download_all_season_images(self, show: Show) -> None:
        """
        Downloads every image type available for every season of the show.
        """
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_IMAGE_DOWNLOADS)

        async def _download_season(season: Season) -> None:
            for image_type in await self.get_available_season_image_types(show, season):
                async with semaphore:
                    await self.download_season_image(show, season, image_type)

        await asyncio.gather(*(_download_season(season) for season in show.seasons))
