from media_manager.config import get_config
from media_manager.mediaServer.abstract_media_server_provider import (
    AbstractMediaServerProvider,
)
from media_manager.mediaServer.jellyfin import JellyfinProvider


def get_media_server_provider() -> AbstractMediaServerProvider | None:
    """
    The configured media server provider, or None when no media server is
    set up. The extension point for a future second provider (Plex, Emby,
    ...): add its config block, provider class, and a branch here.
    """
    config = get_config().media_server
    if config.jellyfin.enabled:
        return JellyfinProvider()
    return None
