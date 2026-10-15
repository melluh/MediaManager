from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from media_manager.torrent.schemas import TorrentMedia

MIN_SCORE = -2
MAX_SCORE = 2
"""Ratings are a signed scale centered on 0: negative means disliked,
positive liked. Like/dislike use -1/+1, leaving +-2 for a stronger opinion;
the five steps also map onto 1-5 stars."""

Score = Annotated[int, Field(ge=MIN_SCORE, le=MAX_SCORE)]


class UserRating(BaseModel):
    """The current user's rating of a movie or show."""

    score: int | None = None
    """None when the user hasn't rated it."""


class SetRating(BaseModel):
    score: Score


class RatingPrompt(BaseModel):
    """A movie the user recently watched but hasn't rated yet."""

    media: TorrentMedia
    watched_at: datetime
