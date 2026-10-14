from pydantic import BaseModel


class MediaServerInfo(BaseModel):
    name: str
    """Identifier of the media server provider, e.g. "jellyfin"."""
    display_name: str
    """Human-readable name, e.g. "Jellyfin"."""


class Meta(BaseModel):
    """
    Static information about this MediaManager instance's setup. It only
    changes when the config does (i.e. on restart), so clients can fetch it
    once and cache it for the whole session.
    """

    media_server: MediaServerInfo | None = None
    """The configured media server, or None when there isn't one."""
