import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from media_manager.auth.db import MediaServerAccount, User
from media_manager.auth.users import current_superuser
from media_manager.database import DbSessionDependency
from media_manager.mediaServer.abstract_media_server_provider import (
    AbstractMediaServerProvider,
)
from media_manager.mediaServer.manager import get_media_server_provider
from media_manager.mediaServer.schemas import MediaServerUserOption

log = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(current_superuser)])


def require_media_server_provider() -> AbstractMediaServerProvider:
    provider = get_media_server_provider()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No media server is configured.",
        )
    return provider


media_server_provider_dep = Annotated[
    AbstractMediaServerProvider, Depends(require_media_server_provider)
]


@router.get("/users", status_code=status.HTTP_200_OK)
async def get_media_server_users(
    db: DbSessionDependency,
    provider: media_server_provider_dep,
) -> list[MediaServerUserOption]:
    """
    All accounts on the media server, for linking them to MediaManager users,
    along with which user each one is already linked to.
    """
    try:
        users = await provider.list_users()
    except Exception as exc:
        log.warning("Could not list media server users", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch users from {provider.display_name}.",
        ) from exc

    stmt = (
        select(MediaServerAccount.external_user_id, User)
        .join(User, User.id == MediaServerAccount.user_id)
        .where(MediaServerAccount.provider == provider.name)
    )
    linked_users = dict((await db.execute(stmt)).unique().tuples().all())
    options = []
    for user in sorted(users, key=lambda u: u.name.casefold()):
        linked_user = linked_users.get(user.id)
        options.append(
            MediaServerUserOption(
                id=user.id,
                name=user.name,
                linked_user_id=linked_user.id if linked_user else None,
                linked_user_name=(linked_user.display_name or linked_user.email)
                if linked_user
                else None,
            )
        )
    return options
