import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from media_manager.mediaServer.schemas import PlayedMediaItem
from tests.mediaServer.test_jellyfin_users import _provider

SINCE = datetime(2026, 10, 1, tzinfo=UTC)


def _item(last_played: str | None, provider_ids: dict | None = None) -> dict:
    return {
        "Id": "x",
        "ProviderIds": provider_ids or {},
        "UserData": {"Played": True, "LastPlayedDate": last_played},
    }


def test_requests_users_played_movies_most_recent_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"Items": [], "TotalRecordCount": 0})

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    assert asyncio.run(provider.get_recently_played_movies("u1", SINCE)) == []
    params = requests[0].url.params
    assert requests[0].url.path == "/Items"
    assert params["userId"] == "u1"
    assert params["IsPlayed"] == "true"
    assert params["IncludeItemTypes"] == "Movie"
    assert params["SortBy"] == "DatePlayed"
    assert params["SortOrder"] == "Descending"


def test_normalizes_provider_ids_and_parses_play_dates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(
            200,
            json={
                "Items": [
                    _item(
                        "2026-10-14T20:15:03.1234567Z",
                        {"Tmdb": "603", "Imdb": "tt0133093", "Tvdb": ""},
                    )
                ]
            },
        )

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    assert asyncio.run(provider.get_recently_played_movies("u1", SINCE)) == [
        PlayedMediaItem(
            provider_ids={"tmdb": "603", "imdb": "tt0133093"},
            last_played_at=datetime(2026, 10, 14, 20, 15, 3, 123456, tzinfo=UTC),
        )
    ]


def test_stops_at_items_played_before_since_and_skips_undated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # noqa: ARG001
        return httpx.Response(
            200,
            json={
                "Items": [
                    _item(None, {"Tmdb": "1"}),
                    _item("2026-10-10T00:00:00Z", {"Tmdb": "2"}),
                    _item("2026-09-01T00:00:00Z", {"Tmdb": "3"}),
                    _item("2026-10-12T00:00:00Z", {"Tmdb": "4"}),
                ]
            },
        )

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    played = asyncio.run(provider.get_recently_played_movies("u1", SINCE))
    assert [item.provider_ids["tmdb"] for item in played] == ["2"]
