from fastapi import APIRouter, Depends

from media_manager.auth.users import current_active_user
from media_manager.health.registry import get_health_registry
from media_manager.health.schemas import SystemHealth

router = APIRouter()


@router.get(
    "/services",
    dependencies=[Depends(current_active_user)],
    description="Health status of all configured external services",
)
def get_service_health() -> SystemHealth:
    return get_health_registry().get_all()
