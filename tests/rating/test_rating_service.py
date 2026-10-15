"""
The dashboard asks users whether they enjoyed movies they recently watched on
the media server, matched to library movies by their external ids.
"""

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from media_manager.mediaServer.schemas import PlayedMediaItem
from media_manager.rating import service as rating_service_module
from media_manager.rating.service import MAX_RATING_PROMPTS, RatingService
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
        provider_ids=provider_ids, last_played_at=NOW - timedelta(hours=hours_ago)
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


class FakeProvider:
    name = "jellyfin"
    display_name = "Jellyfin"

    def __init__(self, played: list[PlayedMediaItem] | Exception) -> None:
        self.played = played
        self.calls: list[str] = []

    async def get_recently_played_movies(
        self,
        user_id: str,
        since: datetime,  # noqa: ARG002
    ) -> list[PlayedMediaItem]:
        self.calls.append(user_id)
        if isinstance(self.played, Exception):
            raise self.played
        return self.played


def _user(linked: bool = True) -> SimpleNamespace:
    accounts = (
        [SimpleNamespace(provider="jellyfin", external_user_id="jf-user")]
        if linked
        else []
    )
    return SimpleNamespace(id=uuid.uuid4(), media_server_accounts=accounts)


def _prompts(
    monkeypatch: pytest.MonkeyPatch,
    provider: FakeProvider | None,
    repository: FakeRatingRepository,
    user: SimpleNamespace | None = None,
) -> list:
    monkeypatch.setattr(
        rating_service_module, "get_media_server_provider", lambda: provider
    )
    service = RatingService(repository)  # type: ignore[arg-type]
    return asyncio.run(service.get_rating_prompts(user or _user()))  # type: ignore[arg-type]


def test_no_prompts_without_media_server(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _prompts(monkeypatch, None, FakeRatingRepository([_movie(1)])) == []


def test_no_prompts_without_linked_account(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeProvider([_played(1, tmdb="1")])

    assert (
        _prompts(
            monkeypatch,
            provider,
            FakeRatingRepository([_movie(1)]),
            _user(linked=False),
        )
        == []
    )
    assert provider.calls == []


def test_no_prompts_when_media_server_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeProvider(RuntimeError("down"))

    assert _prompts(monkeypatch, provider, FakeRatingRepository([_movie(1)])) == []


def test_matches_by_imdb_and_by_provider_id(monkeypatch: pytest.MonkeyPatch) -> None:
    by_imdb = _movie(10, imdb_id="tt10")
    by_tmdb = _movie(20)
    by_tvdb = _movie(30, metadata_provider="tvdb")
    not_watched = _movie(40)
    provider = FakeProvider(
        [
            _played(1, imdb="tt10", tmdb="999"),
            _played(2, tmdb="20"),
            _played(3, tvdb="30"),
            _played(4, tmdb="not-a-number"),
        ]
    )

    prompts = _prompts(
        monkeypatch,
        provider,
        FakeRatingRepository([by_imdb, by_tmdb, by_tvdb, not_watched]),
    )

    assert [p.media.id for p in prompts] == [by_imdb.id, by_tmdb.id, by_tvdb.id]
    assert prompts[0].watched_at == NOW - timedelta(hours=1)
    assert provider.calls == ["jf-user"]


def test_skips_rated_or_dismissed_movies(monkeypatch: pytest.MonkeyPatch) -> None:
    answered = _movie(1)
    unanswered = _movie(2)
    provider = FakeProvider([_played(1, tmdb="1"), _played(2, tmdb="2")])

    prompts = _prompts(
        monkeypatch,
        provider,
        FakeRatingRepository([answered, unanswered], answered={answered.id}),
    )

    assert [p.media.id for p in prompts] == [unanswered.id]


def test_rewatched_movie_is_asked_about_once_with_latest_watch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    movie = _movie(1)
    provider = FakeProvider([_played(1, tmdb="1"), _played(50, tmdb="1")])

    prompts = _prompts(monkeypatch, provider, FakeRatingRepository([movie]))

    assert len(prompts) == 1
    assert prompts[0].watched_at == NOW - timedelta(hours=1)


def test_prompts_are_capped(monkeypatch: pytest.MonkeyPatch) -> None:
    count = MAX_RATING_PROMPTS + 5
    movies = [_movie(i) for i in range(count)]
    provider = FakeProvider([_played(i, tmdb=str(i)) for i in range(count)])

    prompts = _prompts(monkeypatch, provider, FakeRatingRepository(movies))

    assert [p.media.id for p in prompts] == [m.id for m in movies[:MAX_RATING_PROMPTS]]
