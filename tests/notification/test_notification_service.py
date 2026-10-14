"""
In-app notifications belong to a single user: a download's notifications go
only to the user who started it, while the external providers (configured
server-wide) keep receiving everything as an admin feed.
"""

import asyncio
import uuid

from media_manager.movies.importer import MovieImportService
from media_manager.movies.schemas import Movie
from media_manager.notification.schemas import Notification
from media_manager.notification.service import NotificationService
from media_manager.torrent.schemas import Torrent, TorrentStatus
from media_manager.tv.importer import TvImportService
from media_manager.tv.schemas import Show


class FakeNotificationRepository:
    def __init__(self) -> None:
        self.saved: list[Notification] = []

    async def save_notification(self, notification: Notification) -> None:
        self.saved.append(notification)


class FakeNotificationManager:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_notification(self, title: str, message: str) -> None:
        self.sent.append((title, message))


class FakeTorrentRepository:
    async def save_torrent(self, torrent: Torrent) -> Torrent:
        return torrent


class FakeTorrentService:
    def __init__(self) -> None:
        self.torrent_repository = FakeTorrentRepository()


def _notification_service() -> tuple[
    NotificationService, FakeNotificationRepository, FakeNotificationManager
]:
    repository = FakeNotificationRepository()
    manager = FakeNotificationManager()
    service = NotificationService(notification_repository=repository)
    service.notification_manager = manager
    return service, repository, manager


def _torrent(initiated_by_user_id: uuid.UUID | None) -> Torrent:
    return Torrent(
        status=TorrentStatus.finished,
        title="Some.Release",
        imported=False,
        hash="x",
        initiated_by_user_id=initiated_by_user_id,
    )


def test_a_notification_for_a_user_is_saved_for_them_and_sent_to_providers():
    service, repository, manager = _notification_service()
    user_id = uuid.uuid4()
    movie_id = uuid.uuid4()

    asyncio.run(
        service.send_notification(
            "Title", "Message", user_id=user_id, movie_id=movie_id
        )
    )

    assert manager.sent == [("Title", "Message")]
    assert len(repository.saved) == 1
    saved = repository.saved[0]
    assert saved.user_id == user_id
    assert saved.movie_id == movie_id
    assert saved.show_id is None
    assert saved.message == "Title: Message"


def test_a_notification_without_a_user_only_goes_to_providers():
    service, repository, manager = _notification_service()

    asyncio.run(service.send_notification("Title", "Message", user_id=None))

    assert manager.sent == [("Title", "Message")]
    assert repository.saved == []


def test_a_movie_import_success_notifies_the_downloader_and_links_the_movie():
    notification_service, repository, _ = _notification_service()
    importer = MovieImportService(
        movie_repository=None,
        torrent_service=FakeTorrentService(),
        notification_service=notification_service,
        movie_metadata_service=None,
    )
    user_id = uuid.uuid4()
    movie = Movie(
        name="The Movie",
        overview="",
        year=2024,
        external_id=1,
        metadata_provider="tmdb",
    )

    asyncio.run(
        importer.notify_import_success(
            _torrent(user_id), movie.name, "movie", media_id=movie.id
        )
    )

    assert [(n.user_id, n.movie_id, n.show_id) for n in repository.saved] == [
        (user_id, movie.id, None)
    ]


def test_a_show_import_failure_notifies_the_downloader_and_links_the_show():
    notification_service, repository, _ = _notification_service()
    importer = TvImportService(
        tv_repository=None,
        torrent_service=FakeTorrentService(),
        notification_service=notification_service,
        tv_metadata_service=None,
    )
    user_id = uuid.uuid4()
    show = Show(
        name="The Show",
        overview="",
        year=2005,
        external_id=1,
        metadata_provider="tvdb",
        seasons=[],
    )

    asyncio.run(
        importer.notify_import_failure(
            _torrent(user_id), show.name, "TV show", "Broken", media_id=show.id
        )
    )

    assert [(n.user_id, n.movie_id, n.show_id) for n in repository.saved] == [
        (user_id, None, show.id)
    ]


def test_an_import_of_a_torrent_with_no_known_downloader_notifies_no_user():
    notification_service, repository, manager = _notification_service()
    importer = MovieImportService(
        movie_repository=None,
        torrent_service=FakeTorrentService(),
        notification_service=notification_service,
        movie_metadata_service=None,
    )

    asyncio.run(importer.notify_import_success(_torrent(None), "The Movie", "movie"))

    assert repository.saved == []
    assert len(manager.sent) == 1
