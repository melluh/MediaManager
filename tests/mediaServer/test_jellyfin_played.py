import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from media_manager.mediaServer.schemas import PlayedMediaItem
from media_manager.metadataProvider.schemas import MediaType
from tests.mediaServer.test_jellyfin_users import _provider

SINCE = datetime(2026, 10, 1, tzinfo=UTC)


def _item(
    last_played: str | None,
    provider_ids: dict | None = None,
    item_id: str = "x",
    **fields: str,
) -> dict:
    return {
        "Id": item_id,
        "Name": f"Item {item_id}",
        "ProviderIds": provider_ids or {},
        "UserData": {"Played": True, "LastPlayedDate": last_played},
        **fields,
    }


def test_requests_users_played_movies_most_recent_first(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"Items": [], "TotalRecordCount": 0})

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    assert asyncio.run(provider.get_played_media("u1", MediaType.movie, SINCE)) == []
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
                        item_id="m1",
                    )
                ],
                "TotalRecordCount": 1,
            },
        )

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    assert asyncio.run(provider.get_played_media("u1", MediaType.movie, SINCE)) == [
        PlayedMediaItem(
            media_type=MediaType.movie,
            server_item_id="m1",
            name="Item m1",
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
                ],
                "TotalRecordCount": 4,
            },
        )

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    played = asyncio.run(provider.get_played_media("u1", MediaType.movie, SINCE))
    assert [item.provider_ids["tmdb"] for item in played] == ["2"]


def test_whole_history_pages_through_everything_including_undated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pages = [
        [
            _item("2026-10-10T00:00:00Z", item_id="a"),
            _item("2025-01-01T00:00:00Z", item_id="b"),
        ],
        [_item(None, item_id="c")],
    ]
    starts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        start = request.url.params["StartIndex"]
        starts.append(start)
        page = pages[0] if start == "0" else pages[1]
        return httpx.Response(200, json={"Items": page, "TotalRecordCount": 3})

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    played = asyncio.run(provider.get_played_media("u1", MediaType.movie))
    assert [item.server_item_id for item in played] == ["a", "b", "c"]
    assert played[2].last_played_at is None
    assert starts == ["0", "2"]


def test_shows_are_the_series_of_played_episodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        params = request.url.params
        if params.get("IncludeItemTypes") == "Episode":
            episodes = [
                _item("2026-10-12T00:00:00Z", item_id="e1", SeriesId="s1"),
                _item("2026-10-11T00:00:00Z", item_id="e2", SeriesId="s2"),
                _item("2026-10-10T00:00:00Z", item_id="e3", SeriesId="s1"),
            ]
            return httpx.Response(200, json={"Items": episodes, "TotalRecordCount": 3})
        assert params["Ids"] == "s1,s2"
        series = [
            _item(None, {"Tvdb": "81189"}, item_id="s2"),
            _item(None, {"Tmdb": "1396"}, item_id="s1"),
        ]
        return httpx.Response(200, json={"Items": series, "TotalRecordCount": 2})

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    played = asyncio.run(provider.get_played_media("u1", MediaType.tv, SINCE))
    assert [(item.server_item_id, item.provider_ids) for item in played] == [
        ("s1", {"tmdb": "1396"}),
        ("s2", {"tvdb": "81189"}),
    ]
    assert all(item.media_type == MediaType.tv for item in played)
    # The series' latest episode play, not the series' own (missing) date.
    assert played[0].last_played_at == datetime(2026, 10, 12, tzinfo=UTC)
    assert len(requests) == 2
