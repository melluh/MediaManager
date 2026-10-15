import logging
from datetime import datetime
from uuid import UUID

from media_manager.auth.db import User
from media_manager.mediaServer.manager import get_media_server_provider
from media_manager.mediaServer.schemas import PlayedMediaItem
from media_manager.metadataProvider.schemas import MediaType
from media_manager.watch_history.models import MediaWatch
from media_manager.watch_history.repository import WatchHistoryRepository

log = logging.getLogger(__name__)


class WatchHistoryService:
    """
    The one way to ask the media server what a user has watched. Every fetch
    is also saved, so live lookups (like the rating prompt's) keep the stored
    history current between full syncs.
    """

    def __init__(self, watch_history_repository: WatchHistoryRepository) -> None:
        self.watch_history_repository = watch_history_repository

    async def fetch_played(
        self, user: User, media_type: MediaType, since: datetime | None = None
    ) -> list[PlayedMediaItem]:
        """
        Movies or shows the user played on the media server, most recently
        played first. Without `since`, this is their whole history and
        replaces the stored one.

        Empty when no media server is configured, the user has no account
        linked on it, or it can't be reached.
        """
        provider = get_media_server_provider()
        if provider is None:
            return []
        account = next(
            (a for a in user.media_server_accounts if a.provider == provider.name),
            None,
        )
        if account is None:
            return []

        try:
            played = await provider.get_played_media(
                account.external_user_id, media_type, since=since
            )
        except Exception:
            log.warning(
                f"Could not fetch played {media_type.value} items from {provider.display_name}",
                exc_info=True,
            )
            return []

        await self.watch_history_repository.save_watches(
            user.id, media_type, played, replace=since is None
        )
        return played

    async def get_watches(
        self, user_id: UUID, media_type: MediaType
    ) -> list[MediaWatch]:
        """The user's stored watch history, as of the last fetch."""
        return await self.watch_history_repository.get_watches(user_id, media_type)

    async def sync_all_users(self) -> None:
        """Re-fetches the whole watch history of every linked user."""
        provider = get_media_server_provider()
        if provider is None:
            return
        users = await self.watch_history_repository.get_users_with_account(
            provider.name
        )
        log.info(f"Syncing watch history of {len(users)} users")
        for user in users:
            for media_type in MediaType:
                await self.fetch_played(user, media_type)
