from typing import Annotated

from fastapi import APIRouter, Depends, status

from media_manager.auth.db import User
from media_manager.auth.users import current_active_user
from media_manager.notification.dependencies import notification_service_dep
from media_manager.notification.schemas import Notification, NotificationId

router = APIRouter()


# --------------------------------
# GET NOTIFICATIONS
# --------------------------------


@router.get(
    "",
    dependencies=[Depends(current_active_user)],
)
async def get_all_notifications(
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> list[Notification]:
    """
    Get all notifications of the current user.
    """
    return await notification_service.get_all_notifications(user_id=user.id)


@router.get(
    "/unread",
    dependencies=[Depends(current_active_user)],
)
async def get_unread_notifications(
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> list[Notification]:
    """
    Get all unread notifications of the current user.
    """
    return await notification_service.get_unread_notifications(user_id=user.id)


@router.get(
    "/unread/count",
    dependencies=[Depends(current_active_user)],
)
async def get_unread_notification_count(
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> int:
    """
    Get the count of unread notifications of the current user.
    """
    return await notification_service.get_unread_notification_count(user_id=user.id)


@router.get(
    "/{notification_id}",
    dependencies=[Depends(current_active_user)],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
    },
)
async def get_notification(
    notification_id: NotificationId,
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> Notification:
    """
    Get a specific notification by ID.
    """
    return await notification_service.get_notification(
        nid=notification_id, user_id=user.id
    )


# --------------------------------
# MANAGE NOTIFICATIONS
# --------------------------------


@router.patch(
    "/read",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_active_user)],
)
async def mark_all_notifications_as_read(
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    """
    Mark all notifications of the current user as read.
    """
    await notification_service.mark_all_notifications_as_read(user_id=user.id)


@router.patch(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_active_user)],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
    },
)
async def mark_notification_as_read(
    notification_id: NotificationId,
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    """
    Mark a notification as read.
    """
    await notification_service.mark_notification_as_read(
        nid=notification_id, user_id=user.id
    )


@router.patch(
    "/{notification_id}/unread",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_active_user)],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
    },
)
async def mark_notification_as_unread(
    notification_id: NotificationId,
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    """
    Mark a notification as unread.
    """
    await notification_service.mark_notification_as_unread(
        nid=notification_id, user_id=user.id
    )


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_active_user)],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Notification not found"},
    },
)
async def delete_notification(
    notification_id: NotificationId,
    notification_service: notification_service_dep,
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    """
    Delete a notification.
    """
    await notification_service.delete_notification(nid=notification_id, user_id=user.id)
