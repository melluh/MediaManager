from typing import Annotated, Any

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from fastapi.params import Depends

from media_manager.audit_log.dependencies import audit_log_service_dep
from media_manager.audit_log.schemas import AuditAction
from media_manager.audit_log.service import AuditLogService, media_label
from media_manager.auth.db import User
from media_manager.auth.users import current_active_user, current_superuser
from media_manager.exceptions import InvalidConfigError
from media_manager.torrent.dependencies import (
    torrent_dep,
    torrent_repository_dep,
    torrent_service_dep,
)
from media_manager.torrent.schemas import Torrent, TorrentStatus, TorrentWithProgress
from media_manager.torrent.service import TorrentService

router = APIRouter()


async def _media_details(service: TorrentService, torrent: Torrent) -> dict[str, Any]:
    """The movie or show a torrent is for, to record alongside an action on it."""
    movie = await service.get_movie_of_torrent(torrent=torrent)
    if movie is not None:
        return {
            "media_type": "movie",
            "media_id": str(movie.id),
            "media_label": media_label(movie),
        }
    show = await service.get_show_of_torrent(torrent=torrent)
    if show is not None:
        return {
            "media_type": "show",
            "media_id": str(show.id),
            "media_label": media_label(show),
        }
    return {}


async def _record_torrent_action(
    audit: AuditLogService,
    action: AuditAction,
    torrent: Torrent,
    details: dict[str, Any],
) -> None:
    await audit.record(
        action,
        subject_type="torrent",
        subject_id=torrent.id,
        subject_label=torrent.title,
        details=details,
    )


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_active_user)],
)
async def get_all_torrents(service: torrent_service_dep) -> list[Torrent]:
    return await service.get_all_torrents()


@router.get(
    "/mine",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_active_user)],
)
async def get_own_torrents(
    service: torrent_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> list[TorrentWithProgress]:
    """
    Get the torrents initiated by the current user that are still downloading,
    along with their current status.
    """
    return await service.get_own_torrents(user_id=user.id)


@router.get(
    "/{torrent_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_active_user)],
)
async def get_torrent(service: torrent_service_dep, torrent: torrent_dep) -> Torrent:
    return await service.get_torrent_by_id(torrent_id=torrent.id)


@router.delete(
    "/{torrent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def delete_torrent(
    service: torrent_service_dep,
    torrent: torrent_dep,
    audit: audit_log_service_dep,
    delete_files: bool = False,
) -> None:
    # Looked up first, since deleting the torrent unlinks it from its media.
    details = await _media_details(service, torrent)
    if delete_files:
        try:
            await service.cancel_download(torrent=torrent, delete_files=False)
        except (RuntimeError, InvalidConfigError):
            pass

    await service.delete_torrent(torrent_id=torrent.id)
    await _record_torrent_action(
        audit,
        AuditAction.download_deleted,
        torrent,
        {**details, "delete_files": delete_files},
    )


@router.post(
    "/{torrent_id}/cancel",
    status_code=status.HTTP_200_OK,
)
async def cancel_torrent(
    service: torrent_service_dep,
    torrent: torrent_dep,
    user: Annotated[User, Depends(current_active_user)],
    audit: audit_log_service_dep,
    remove_from_client: bool = False,
) -> Torrent:
    """
    Cancels a torrent the current user initiated: hides it from their
    homepage and stops it from being imported, without deleting it, and
    optionally removes it from the download client (without deleting its
    downloaded data).
    """
    if torrent.initiated_by_user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own downloads",
        )
    cancelled_torrent = await service.cancel_torrent(
        torrent=torrent, remove_from_client=remove_from_client
    )
    await _record_torrent_action(
        audit,
        AuditAction.download_cancelled,
        torrent,
        {
            **await _media_details(service, torrent),
            "remove_from_client": remove_from_client,
        },
    )
    return cancelled_torrent


@router.post(
    "/{torrent_id}/retry",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def retry_torrent_download(
    service: torrent_service_dep,
    torrent: torrent_dep,
    audit: audit_log_service_dep,
) -> None:
    await service.pause_download(torrent=torrent)
    await service.resume_download(torrent=torrent)
    await _record_torrent_action(
        audit,
        AuditAction.download_retried,
        torrent,
        await _media_details(service, torrent),
    )


@router.patch(
    "/{torrent_id}/status",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def update_torrent_status(
    rep: torrent_repository_dep,
    service: torrent_service_dep,
    torrent: torrent_dep,
    audit: audit_log_service_dep,
    state: TorrentStatus | None = None,
    imported: bool | None = None,
) -> Torrent:
    changes: dict[str, Any] = {}
    if imported is not None and imported != torrent.imported:
        changes["imported"] = {"from": torrent.imported, "to": imported}
    if state is not None and state != torrent.status:
        changes["status"] = {"from": torrent.status.name, "to": state.name}
    if imported is not None:
        torrent.imported = imported
        torrent.import_error = None
    if state is not None:
        torrent.status = state
    if state is None and imported is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No status or imported value provided",
        )

    await rep.save_torrent(torrent=torrent)
    await _record_torrent_action(
        audit,
        AuditAction.download_status_changed,
        torrent,
        {**await _media_details(service, torrent), "changes": changes},
    )
    return torrent
