import asyncio

import httpx
import pytest

from media_manager.mediaServer import jellyfin
from media_manager.mediaServer.jellyfin import JellyfinProvider
from media_manager.mediaServer.schemas import MediaServerUser


def _provider(
    monkeypatch: pytest.MonkeyPatch, handler: httpx.MockTransport
) -> tuple[JellyfinProvider, list[str]]:
    monkeypatch.setattr(jellyfin, "_client", httpx.AsyncClient(transport=handler))
    provider = JellyfinProvider.__new__(JellyfinProvider)
    provider.url = "http://jellyfin"
    provider.external_url = "http://jellyfin"
    provider.api_key = "key"
    unavailable: list[str] = []
    monkeypatch.setattr(provider, "_report_unavailable", unavailable.append)
    return provider, unavailable


def test_list_users_maps_id_and_name(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Users"
        return httpx.Response(
            200,
            json=[
                {"Id": "a1", "Name": "alice", "Policy": {}},
                {"Id": "b2", "Name": "bob"},
            ],
        )

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    assert asyncio.run(provider.list_users()) == [
        MediaServerUser(id="a1", name="alice"),
        MediaServerUser(id="b2", name="bob"),
    ]


def test_get_user_returns_user(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/Users/a1"
        return httpx.Response(200, json={"Id": "a1", "Name": "alice"})

    provider, _ = _provider(monkeypatch, httpx.MockTransport(handler))

    assert asyncio.run(provider.get_user("a1")) == MediaServerUser(
        id="a1", name="alice"
    )


@pytest.mark.parametrize("status_code", [400, 404])
def test_get_user_missing_returns_none_without_marking_unavailable(
    monkeypatch: pytest.MonkeyPatch, status_code: int
) -> None:
    provider, unavailable = _provider(
        monkeypatch, httpx.MockTransport(lambda _: httpx.Response(status_code))
    )

    assert asyncio.run(provider.get_user("missing")) is None
    assert unavailable == []


def test_get_user_server_error_raises_and_marks_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, unavailable = _provider(
        monkeypatch, httpx.MockTransport(lambda _: httpx.Response(500))
    )

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(provider.get_user("a1"))
    assert len(unavailable) == 1
