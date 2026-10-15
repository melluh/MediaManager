from abc import ABC, abstractmethod
from datetime import datetime

from media_manager.health.registry import get_health_registry
from media_manager.health.schemas import ServiceStatus
from media_manager.mediaServer.schemas import MediaServerUser, PlayedMediaItem
from media_manager.metadataProvider.schemas import MediaType


class AbstractMediaServerProvider(ABC):
    """
    A media server (Jellyfin, and potentially others like Plex/Emby in the
    future) that can be asked whether it already has a given movie/show
    indexed, and if so, link straight to it for playback.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """
        Human-readable name shown to users, e.g. in "Watch on <display_name>"
        buttons. Unlike `name`, this is never used as an identifier.
        """

    @abstractmethod
    async def find_watch_url(
        self,
        *,
        imdb_id: str | None,
        external_id: int,
        metadata_provider: str,
    ) -> str | None:
        """
        A browser-facing deep link to this item on the media server, or None
        if the server has no matching item (e.g. it hasn't scanned a
        recently-downloaded file in yet).
        """
        raise NotImplementedError()

    @abstractmethod
    async def list_users(self) -> list[MediaServerUser]:
        """
        All user accounts on the media server, for linking them to
        MediaManager users.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_user(self, user_id: str) -> MediaServerUser | None:
        """
        The media server account with this id, or None if it doesn't exist.
        """
        raise NotImplementedError()

    @abstractmethod
    async def get_played_media(
        self, user_id: str, media_type: MediaType, since: datetime | None = None
    ) -> list[PlayedMediaItem]:
        """
        Movies or shows the media server account `user_id` has watched, most
        recently played first.

        :param since: Only items last played at or after this time, which also
            leaves out items without a play date. None for the whole history.
        """
        raise NotImplementedError()

    @abstractmethod
    async def ping(self) -> bool:
        """
        Check whether the media server is reachable.

        :return: True if the server responds successfully, False otherwise.
        """
        raise NotImplementedError()

    def _report_unavailable(self, message: str) -> None:
        """
        Mark this media server unavailable in the health registry. Called when
        any request to it fails; the periodic health check marks it healthy
        again once a ping succeeds.
        """
        get_health_registry().update(
            self.name, self.display_name, ServiceStatus.unavailable, message
        )
