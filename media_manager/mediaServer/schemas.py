from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MediaServerUser(BaseModel):
    """An account on the media server, as reported by the server itself."""

    id: str
    name: str


class MediaServerUserOption(MediaServerUser):
    """A media server account offered when linking it to a MediaManager user."""

    linked_user_id: UUID | None = None
    """The MediaManager user this account is already linked to, if any."""
    linked_user_name: str | None = None
    """That user's display name, falling back to their email."""


class PlayedMediaItem(BaseModel):
    """An item a media server user has watched, as reported by the server."""

    provider_ids: dict[str, str]
    """External ids keyed by our metadata provider names ("imdb", "tmdb",
    "tvdb"), for matching the item to library media."""
    last_played_at: datetime
