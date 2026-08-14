import logging
from abc import ABC, abstractmethod

from media_manager.config import MediaManagerConfig
from media_manager.metadataProvider.schemas import (
    MediaImageType,
    MediaType,
    MetaDataProviderSearchResult,
)
from media_manager.movies.schemas import Movie
from media_manager.tv.schemas import Show

log = logging.getLogger(__name__)


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
        given media item.
        """
        for image_type in await self.get_available_image_types(media, media_type):
            await self.download_media_image(media, media_type, image_type)
