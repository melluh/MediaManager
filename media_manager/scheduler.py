import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import taskiq_fastapi
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from taskiq import TaskiqDepends, TaskiqScheduler
from taskiq.cli.scheduler.run import SchedulerLoop
from taskiq_postgresql import PostgresqlBroker
from taskiq_postgresql.scheduler_source import PostgresqlSchedulerSource

from media_manager.database import get_async_session
from media_manager.indexer.models import IndexerQueryResult
from media_manager.movies.dependencies import (
    get_movie_import_service,
    get_movie_service,
)
from media_manager.movies.importer import MovieImportService
from media_manager.movies.service import MovieService
from media_manager.notification.dependencies import get_notification_service
from media_manager.notification.service import NotificationService
from media_manager.titleIndex.download import refresh_title_index
from media_manager.torrent.dependencies import get_torrent_service
from media_manager.torrent.service import TorrentService
from media_manager.tv.dependencies import get_tv_import_service, get_tv_service
from media_manager.tv.importer import TvImportService
from media_manager.tv.service import TvService

INDEXER_QUERY_RESULT_EXPIRY = timedelta(hours=6)


def _build_db_connection_string_for_taskiq() -> str:
    from media_manager.config import MediaManagerConfig

    db_config = MediaManagerConfig().database
    user = quote(db_config.user, safe="")
    password = quote(db_config.password, safe="")
    dbname = quote(db_config.dbname, safe="")
    host = quote(str(db_config.host), safe="")
    port = quote(str(db_config.port), safe="")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


broker = PostgresqlBroker(
    dsn=_build_db_connection_string_for_taskiq,
    driver="psycopg",
    run_migrations=True,
)

# Register FastAPI app with the broker so worker processes can resolve FastAPI
# dependencies. Using a string reference avoids circular imports.
taskiq_fastapi.init(broker, "media_manager.main:app")

log = logging.getLogger(__name__)


@broker.task
async def import_all_movie_torrents_task(
    movie_service: MovieService = TaskiqDepends(get_movie_service),
) -> None:
    log.info("Importing all Movie torrents")
    await movie_service.import_all_torrents()


@broker.task
async def import_all_show_torrents_task(
    tv_service: TvService = TaskiqDepends(get_tv_service),
) -> None:
    log.info("Importing all Show torrents")
    await tv_service.import_all_torrents()


@broker.task
async def flag_orphaned_torrents_task(
    torrent_service: TorrentService = TaskiqDepends(get_torrent_service),
    notification_service: NotificationService = TaskiqDepends(get_notification_service),
) -> None:
    log.info("Flagging orphaned completed torrents")
    await torrent_service.flag_orphaned_completed_torrents(
        notification_service=notification_service
    )


@broker.task
async def update_all_movies_metadata_task(
    movie_service: MovieService = TaskiqDepends(get_movie_service),
) -> None:
    await movie_service.update_all_metadata()


@broker.task
async def update_all_non_ended_shows_metadata_task(
    tv_service: TvService = TaskiqDepends(get_tv_service),
) -> None:
    await tv_service.update_all_non_ended_shows_metadata()


@broker.task
async def scan_importable_movies_task(
    movie_import_service: MovieImportService = TaskiqDepends(get_movie_import_service),
) -> None:
    log.info("Scanning for importable movies")
    await movie_import_service.rescan_importable_movies()


@broker.task
async def scan_importable_shows_task(
    tv_import_service: TvImportService = TaskiqDepends(get_tv_import_service),
) -> None:
    log.info("Scanning for importable shows")
    await tv_import_service.rescan_importable_tv_shows()


@broker.task
async def refresh_media_file_probes_task(
    movie_service: MovieService = TaskiqDepends(get_movie_service),
    tv_service: TvService = TaskiqDepends(get_tv_service),
) -> None:
    log.info("Refreshing stored media file probes")
    await movie_service.refresh_all_movie_file_details()
    await tv_service.refresh_all_episode_file_details()


@broker.task
async def scan_movie_library_files_task(
    movie_service: MovieService = TaskiqDepends(get_movie_service),
) -> None:
    log.info("Scanning movie library files")
    await movie_service.scan_library_files()


@broker.task
async def scan_show_library_files_task(
    tv_service: TvService = TaskiqDepends(get_tv_service),
) -> None:
    log.info("Scanning TV library files")
    await tv_service.scan_library_files()


@broker.task
async def encode_avif_image_task(image_file_path: str) -> None:
    """
    Encodes the .avif variant of an image already written to disk as
    .jpg/.webp. Enqueued (not scheduled) once per downloaded image - see
    `media_manager.metadataProvider.utils._enqueue_avif_encode` - so avif
    encoding, which is much slower than jpg/webp, never blocks an import.
    """
    from media_manager.metadataProvider.utils import _encode_avif

    await asyncio.to_thread(_encode_avif, Path(image_file_path))


@broker.task
async def refresh_tmdb_title_index_task() -> None:
    from media_manager.config import MediaManagerConfig

    config = MediaManagerConfig()
    log.info("Refreshing TMDB title autocomplete index")
    await refresh_title_index(config.misc.title_index_directory, config.title_index)


@broker.task
async def delete_expired_indexer_query_results_task(
    db: AsyncSession = TaskiqDepends(get_async_session),
) -> None:
    cutoff = datetime.now(UTC) - INDEXER_QUERY_RESULT_EXPIRY
    result = await db.execute(
        delete(IndexerQueryResult).where(IndexerQueryResult.created_at < cutoff)
    )
    await db.commit()
    log.info("Deleted %d expired indexer query results", result.rowcount)


# Maps each task to its cron schedule so PostgresqlSchedulerSource can seed
# the taskiq_schedulers table on first startup.
_STARTUP_SCHEDULES: dict[str, list[dict[str, str]]] = {
    import_all_movie_torrents_task.task_name: [{"cron": "*/2 * * * *"}],
    import_all_show_torrents_task.task_name: [{"cron": "*/2 * * * *"}],
    # Runs less often than the imports above: it only needs to catch torrents
    # neither importer ever claims, not race the normal import window.
    flag_orphaned_torrents_task.task_name: [{"cron": "*/5 * * * *"}],
    update_all_movies_metadata_task.task_name: [{"cron": "0 * * * *"}],
    update_all_non_ended_shows_metadata_task.task_name: [{"cron": "0 * * * *"}],
    scan_importable_movies_task.task_name: [{"cron": "*/5 * * * *"}],
    scan_importable_shows_task.task_name: [{"cron": "*/5 * * * *"}],
    # Stats every media file, but only probes files that are new or changed
    # since their stored probe, so after the first run this is cheap. Imports
    # and viewing a movie's/season's files also refresh them immediately.
    refresh_media_file_probes_task.task_name: [{"cron": "*/15 * * * *"}],
    # Hourly rather than every few minutes: this walks every media directory
    # on disk, and nothing depends on it being immediate - imports record
    # their own paths, and an admin can trigger a scan on demand.
    scan_movie_library_files_task.task_name: [{"cron": "17 * * * *"}],
    scan_show_library_files_task.task_name: [{"cron": "47 * * * *"}],
    delete_expired_indexer_query_results_task.task_name: [{"cron": "*/30 * * * *"}],
    # After TMDB's ~08:00 UTC publish time, with margin.
    refresh_tmdb_title_index_task.task_name: [{"cron": "30 9 * * *"}],
}


def build_scheduler_loop() -> SchedulerLoop:
    source = PostgresqlSchedulerSource(
        dsn=_build_db_connection_string_for_taskiq,
        driver="psycopg",
        broker=broker,
        run_migrations=True,
        startup_schedule=_STARTUP_SCHEDULES,
    )
    scheduler = TaskiqScheduler(broker=broker, sources=[source])
    return SchedulerLoop(scheduler)
