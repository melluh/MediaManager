from fastapi import APIRouter, status
from fastapi.params import Depends

from media_manager.admin.dependencies import admin_service_dep
from media_manager.admin.schemas import DiskUsageStats, LibraryStats
from media_manager.admin.service import AdminService
from media_manager.auth.users import current_superuser
from media_manager.config import get_config

router = APIRouter(dependencies=[Depends(current_superuser)])


@router.get("/stats", status_code=status.HTTP_200_OK)
async def get_admin_stats(service: admin_service_dep) -> LibraryStats:
    return await service.get_stats()


@router.get("/disk-usage", status_code=status.HTTP_200_OK)
async def get_disk_usage() -> DiskUsageStats:
    return await AdminService.get_disk_usage(get_config())
