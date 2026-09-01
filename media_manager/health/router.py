from typing import Annotated

from fastapi import APIRouter, Depends

from media_manager.auth.db import User
from media_manager.auth.users import current_active_user
from media_manager.health.registry import get_health_registry
from media_manager.health.schemas import SystemHealth

router = APIRouter()


@router.get(
    "/services",
    description="Health status of all configured external services",
)
def get_service_health(
    user: Annotated[User, Depends(current_active_user)],
) -> SystemHealth:
    health = get_health_registry().get_all()
    if not user.is_superuser:
        health = health.model_copy(
            update={
                "services": [
                    service.model_copy(update={"message": None})
                    for service in health.services
                ]
            }
        )
    return health
