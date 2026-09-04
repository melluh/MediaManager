from typing import Annotated

from fastapi import APIRouter, status
from fastapi.exceptions import HTTPException
from fastapi.params import Depends

from media_manager.auth.db import User
from media_manager.auth.users import current_active_user, current_superuser
from media_manager.exceptions import InvalidConfigError
from media_manager.torrent.dependencies import (
    torrent_dep,
    torrent_repository_dep,
    torrent_service_dep,
)
from media_manager.torrent.schemas import Torrent, TorrentStatus, TorrentWithProgress

router = APIRouter()


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


@router.get("/{torrent_id}", status_code=status.HTTP_200_OK)
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
    delete_files: bool = False,
) -> None:
    if delete_files:
        try:
            await service.cancel_download(torrent=torrent, delete_files=False)
        except (RuntimeError, InvalidConfigError):
            pass

    await service.delete_torrent(torrent_id=torrent.id)


@router.post(
    "/{torrent_id}/cancel",
    status_code=status.HTTP_200_OK,
)
async def cancel_torrent(
    service: torrent_service_dep,
    torrent: torrent_dep,
    user: Annotated[User, Depends(current_active_user)],
    remove_from_client: bool = False,
) -> Torrent:
    """
    Cancels a torrent the current user initiated: hides it from their
    homepage without deleting it, and optionally removes it from the
    download client (without deleting its downloaded data).
    """
    if torrent.initiated_by_user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only cancel your own downloads",
        )
    return await service.cancel_torrent(
        torrent=torrent, remove_from_client=remove_from_client
    )


@router.post(
    "/{torrent_id}/retry",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def retry_torrent_download(
    service: torrent_service_dep,
    torrent: torrent_dep,
) -> None:
    await service.pause_download(torrent=torrent)
    await service.resume_download(torrent=torrent)


@router.patch(
    "/{torrent_id}/status",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def update_torrent_status(
    rep: torrent_repository_dep,
    torrent: torrent_dep,
    state: TorrentStatus | None = None,
    imported: bool | None = None,
) -> Torrent:
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
    return torrent
