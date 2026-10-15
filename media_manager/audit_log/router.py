import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from media_manager.audit_log.dependencies import audit_log_service_dep
from media_manager.audit_log.schemas import AuditAction, AuditCategory, AuditLogPage
from media_manager.auth.users import current_superuser

router = APIRouter(dependencies=[Depends(current_superuser)])


@router.get("", status_code=status.HTTP_200_OK)
async def get_audit_log(
    service: audit_log_service_dep,
    user_id: uuid.UUID | None = None,
    category: AuditCategory | None = None,
    action: AuditAction | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AuditLogPage:
    """
    The actions users took, newest first. With `user_id`, only the actions
    taken by that user or done to them (e.g. by an admin).
    """
    return await service.get_entries(
        user_id=user_id,
        category=category,
        action=action,
        limit=limit,
        offset=offset,
    )
