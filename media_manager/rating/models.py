from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    SmallInteger,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from media_manager.database import Base


class MediaRating(Base):
    """
    A user's opinion of a movie or show. Exactly one of `movie_id`/`show_id`
    is set.
    """

    __tablename__ = "media_rating"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id"),
        UniqueConstraint("user_id", "show_id"),
        CheckConstraint(
            "(movie_id IS NULL) <> (show_id IS NULL)",
            name="media_rating_one_media",
        ),
        CheckConstraint("score BETWEEN -2 AND 2", name="media_rating_score_range"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    movie_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("movie.id", ondelete="CASCADE"), default=None
    )
    show_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("show.id", ondelete="CASCADE"), default=None
    )
    score: Mapped[int] = mapped_column(SmallInteger)
    """Signed preference, centered on 0: negative is disliked, positive is
    liked. See `rating.schemas.MIN_SCORE`/`MAX_SCORE`."""
    rated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RatingPromptDismissal(Base):
    """
    A movie the user chose not to rate when asked whether they enjoyed it, so
    they aren't asked about it again.
    """

    __tablename__ = "rating_prompt_dismissal"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    movie_id: Mapped[UUID] = mapped_column(
        ForeignKey("movie.id", ondelete="CASCADE"), primary_key=True
    )
    dismissed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
