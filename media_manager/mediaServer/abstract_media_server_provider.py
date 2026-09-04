from abc import ABC, abstractmethod


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
