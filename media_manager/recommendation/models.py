from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from media_manager.database import Base


class TmdbRecommendationList(Base):
    """
    TMDB's "people who liked this also liked" list for one movie or show,
    stored so building a user's recommendations doesn't hit TMDB per title.
    """

    __tablename__ = "tmdb_recommendation_list"

    media_type: Mapped[str] = mapped_column(primary_key=True)
    """A `MediaType` value."""
    tmdb_id: Mapped[int] = mapped_column(primary_key=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    """When the list was last fetched, or last attempted if `results` is
    None."""
    results = mapped_column(JSONB, nullable=True)
    """`MetaDataProviderSearchResult` dumps, best match first. None if the
    last fetch failed (e.g. a metadata relay without the endpoint)."""
