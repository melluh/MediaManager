"""
Every fetch of what a user played on the media server goes through
WatchHistoryService, which also saves it as their watch history.
"""

import asyncio
import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from media_manager.mediaServer.schemas import PlayedMediaItem
from media_manager.metadataProvider.schemas import MediaType
from media_manager.watch_history import service as watch_history_service_module
from media_manager.watch_history.service import WatchHistoryService

SINCE = datetime(2026, 10, 1, tzinfo=UTC)
PLAYED = [
    PlayedMediaItem(
        media_type=MediaType.movie,
        server_item_id="m1",
        name="The Matrix",
        provider_ids={"tmdb": "603"},
        last_played_at=datetime(2026, 10, 14, tzinfo=UTC),
    )
]


class FakeRepository:
    def __init__(self) -> None:
        self.saved: list[tuple] = []

    async def save_watches(
        self,
        user_id: uuid.UUID,
        media_type: MediaType,
        items: list[PlayedMediaItem],
        *,
        replace: bool,
    ) -> None:
        self.saved.append((user_id, media_type, items, replace))


class FakeProvider:
    name = "jellyfin"
    display_name = "Jellyfin"

    def __init__(self, played: list[PlayedMediaItem] | Exception) -> None:
        self.played = played
        self.calls: list[tuple] = []

    async def get_played_media(
        self, user_id: str, media_type: MediaType, since: datetime | None = None
    ) -> list[PlayedMediaItem]:
        self.calls.append((user_id, media_type, since))
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


def _fetch(
    monkeypatch: pytest.MonkeyPatch,
    provider: FakeProvider | None,
    repository: FakeRepository,
    user: SimpleNamespace,
    since: datetime | None = SINCE,
) -> list[PlayedMediaItem]:
    monkeypatch.setattr(
        watch_history_service_module, "get_media_server_provider", lambda: provider
    )
    service = WatchHistoryService(repository)  # type: ignore[arg-type]
    return asyncio.run(service.fetch_played(user, MediaType.movie, since=since))  # type: ignore[arg-type]


def test_nothing_without_media_server(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = FakeRepository()

    assert _fetch(monkeypatch, None, repository, _user()) == []
    assert repository.saved == []


def test_nothing_without_linked_account(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = FakeProvider(PLAYED)
    repository = FakeRepository()

    assert _fetch(monkeypatch, provider, repository, _user(linked=False)) == []
    assert provider.calls == []
    assert repository.saved == []


def test_nothing_saved_when_media_server_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    repository = FakeRepository()

    assert (
        _fetch(monkeypatch, FakeProvider(RuntimeError("down")), repository, _user())
        == []
    )
    # Keeps the stored history rather than wiping it.
    assert repository.saved == []


def test_recent_fetch_is_returned_and_added_to_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = FakeProvider(PLAYED)
    repository = FakeRepository()
    user = _user()

    assert _fetch(monkeypatch, provider, repository, user) == PLAYED
    assert provider.calls == [("jf-user", MediaType.movie, SINCE)]
    assert repository.saved == [(user.id, MediaType.movie, PLAYED, False)]


def test_whole_history_fetch_replaces_stored_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = FakeRepository()
    user = _user()

    _fetch(monkeypatch, FakeProvider(PLAYED), repository, user, since=None)

    assert repository.saved == [(user.id, MediaType.movie, PLAYED, True)]
