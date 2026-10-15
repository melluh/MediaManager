"""
The dashboard asks users whether they enjoyed movies they recently watched on
the media server, matched to library movies by their external ids. Fetching
what they watched is `WatchHistoryService`'s job; see
tests/watch_history/test_watch_history_service.py.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from media_manager.mediaServer.schemas import PlayedMediaItem
from media_manager.metadataProvider.schemas import MediaType
from media_manager.rating.service import (
    MAX_RATING_PROMPTS,
    RATING_PROMPT_LOOKBACK,
    RatingService,
)
from media_manager.torrent.schemas import TorrentMedia

NOW = datetime(2026, 10, 15, tzinfo=UTC)


def _movie(
    external_id: int, imdb_id: str | None = None, metadata_provider: str = "tmdb"
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=f"Movie {external_id}",
        slug=f"movie-{external_id}",
        year=2000,
        metadata_updated_at=None,
        imdb_id=imdb_id,
        metadata_provider=metadata_provider,
        external_id=external_id,
    )


def _played(hours_ago: int, **provider_ids: str) -> PlayedMediaItem:
    return PlayedMediaItem(
        media_type=MediaType.movie,
        server_item_id=str(uuid.uuid4()),
        name="Played",
        provider_ids=provider_ids,
        last_played_at=NOW - timedelta(hours=hours_ago),
    )


class FakeRatingRepository:
    def __init__(
        self, movies: list[SimpleNamespace], answered: set | None = None
    ) -> None:
        self.movies = movies
        self.answered = answered or set()
        self.queries: list[tuple[set, set]] = []

    async def find_movies(self, imdb_ids: set, external_ids: set) -> list:
        self.queries.append((imdb_ids, external_ids))
        return [
            (movie, TorrentMedia.from_media(movie, is_show=False, images={}))
            for movie in self.movies
            if movie.imdb_id in imdb_ids
            or (movie.metadata_provider, movie.external_id) in external_ids
        ]

    async def get_answered_movie_ids(self, user_id: uuid.UUID) -> set:  # noqa: ARG002
        return self.answered


class FakeWatchHistoryService:
    def __init__(self, played: list[PlayedMediaItem]) -> None:
        self.played = played
        self.calls: list[tuple[MediaType, datetime | None]] = []

    async def fetch_played(
        self,
        user: SimpleNamespace,  # noqa: ARG002
        media_type: MediaType,
        since: datetime | None = None,
    ) -> list[PlayedMediaItem]:
        self.calls.append((media_type, since))
        return self.played


def _prompts(
    watch_history: FakeWatchHistoryService, repository: FakeRatingRepository
) -> list:
    service = RatingService(repository, watch_history)  # type: ignore[arg-type]
    user = SimpleNamespace(id=uuid.uuid4())
    return asyncio.run(service.get_rating_prompts(user))  # type: ignore[arg-type]


def test_no_prompts_when_nothing_was_watched() -> None:
    assert _prompts(FakeWatchHistoryService([]), FakeRatingRepository([_movie(1)])) == []


def test_asks_for_recently_played_movies(monkeypatch: pytest.MonkeyPatch) -> None:
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz: object = None) -> datetime:  # noqa: ARG003
            return NOW

    monkeypatch.setattr("media_manager.rating.service.datetime", FixedDatetime)
    watch_history = FakeWatchHistoryService([])

    _prompts(watch_history, FakeRatingRepository([]))

    assert watch_history.calls == [(MediaType.movie, NOW - RATING_PROMPT_LOOKBACK)]


def test_matches_by_imdb_and_by_provider_id() -> None:
    by_imdb = _movie(10, imdb_id="tt10")
    by_tmdb = _movie(20)
    by_tvdb = _movie(30, metadata_provider="tvdb")
    not_watched = _movie(40)
    watch_history = FakeWatchHistoryService(
        [
            _played(1, imdb="tt10", tmdb="999"),
            _played(2, tmdb="20"),
            _played(3, tvdb="30"),
            _played(4, tmdb="not-a-number"),
        ]
    )

    prompts = _prompts(
        watch_history, FakeRatingRepository([by_imdb, by_tmdb, by_tvdb, not_watched])
    )

    assert [p.media.id for p in prompts] == [by_imdb.id, by_tmdb.id, by_tvdb.id]
    assert prompts[0].watched_at == NOW - timedelta(hours=1)


def test_skips_rated_or_dismissed_movies() -> None:
    answered = _movie(1)
    unanswered = _movie(2)
    watch_history = FakeWatchHistoryService([_played(1, tmdb="1"), _played(2, tmdb="2")])

    prompts = _prompts(
        watch_history,
        FakeRatingRepository([answered, unanswered], answered={answered.id}),
    )

    assert [p.media.id for p in prompts] == [unanswered.id]


def test_rewatched_movie_is_asked_about_once_with_latest_watch() -> None:
    movie = _movie(1)
    watch_history = FakeWatchHistoryService([_played(1, tmdb="1"), _played(50, tmdb="1")])

    prompts = _prompts(watch_history, FakeRatingRepository([movie]))

    assert len(prompts) == 1
    assert prompts[0].watched_at == NOW - timedelta(hours=1)


def test_prompts_are_capped() -> None:
    count = MAX_RATING_PROMPTS + 5
    movies = [_movie(i) for i in range(count)]
    watch_history = FakeWatchHistoryService([_played(i, tmdb=str(i)) for i in range(count)])

    prompts = _prompts(watch_history, FakeRatingRepository(movies))

    assert [p.media.id for p in prompts] == [m.id for m in movies[:MAX_RATING_PROMPTS]]
