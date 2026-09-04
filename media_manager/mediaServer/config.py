from pydantic_settings import BaseSettings


class JellyfinConfig(BaseSettings):
    enabled: bool = False
    url: str = "http://localhost:8096"
    """Internal API URL MediaManager talks to."""
    external_url: str | None = None
    """Browser-facing URL for the "Watch on <server>" link, if different from
    `url` (e.g. behind a reverse proxy). Falls back to `url` when unset."""
    api_key: str = ""


class MediaServerConfig(BaseSettings):
    jellyfin: JellyfinConfig = JellyfinConfig()
