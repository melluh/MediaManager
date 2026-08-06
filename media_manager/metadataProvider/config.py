from pydantic_settings import BaseSettings


class TmdbConfig(BaseSettings):
    tmdb_relay_url: str = "https://metadata-relay.dorninger.co/tmdb"
    primary_languages: list[str] = []  # ISO 639-1 language codes
    default_language: str = "en"  # ISO 639-1 language codes


class TvdbConfig(BaseSettings):
    tvdb_relay_url: str = "https://metadata-relay.dorninger.co/tvdb"


class MetadataProviderConfig(BaseSettings):
    tvdb: TvdbConfig = TvdbConfig()
    tmdb: TmdbConfig = TmdbConfig()
    # Minimum time between metadata refetches for a movie/show, in hours
    refetch_interval_hours: int = 24
    # How long to cache external show/movie detail lookups, in hours
    detail_cache_ttl_hours: float = 6
    # How long to cache per-season metadata lookups, in hours
    season_cache_ttl_hours: float = 12
    # How long to cache trending/"recommended" lists, in hours
    trending_cache_ttl_hours: float = 4
