from typing import Annotated

from fastapi import Depends

from media_manager.database import DbSessionDependency
from media_manager.watch_history.repository import WatchHistoryRepository
from media_manager.watch_history.service import WatchHistoryService


def get_watch_history_repository(
    db_session: DbSessionDependency,
) -> WatchHistoryRepository:
    return WatchHistoryRepository(db_session)


watch_history_repository_dep = Annotated[
    WatchHistoryRepository, Depends(get_watch_history_repository)
]


def get_watch_history_service(
    watch_history_repository: watch_history_repository_dep,
) -> WatchHistoryService:
    return WatchHistoryService(watch_history_repository)


watch_history_service_dep = Annotated[
    WatchHistoryService, Depends(get_watch_history_service)
]
