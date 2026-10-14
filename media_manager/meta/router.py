from fastapi import APIRouter, Depends, status

from media_manager.auth.users import current_active_user
from media_manager.mediaServer.manager import get_media_server_provider
from media_manager.meta.schemas import MediaServerInfo, Meta

router = APIRouter(dependencies=[Depends(current_active_user)])


@router.get("", status_code=status.HTTP_200_OK)
def get_meta() -> Meta:
    """
    Static information about this instance's setup, such as the configured
    media server. Fetched once per session by the frontend rather than
    repeated on every endpoint that needs it.
    """
    media_server = get_media_server_provider()
    return Meta(
        media_server=MediaServerInfo(
            name=media_server.name, display_name=media_server.display_name
        )
        if media_server is not None
        else None
    )
