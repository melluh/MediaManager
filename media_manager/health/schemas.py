from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class ServiceStatus(StrEnum):
    healthy = "healthy"
    unavailable = "unavailable"
    unknown = "unknown"


class ServiceHealth(BaseModel):
    name: str
    display_name: str
    status: ServiceStatus
    message: str | None = None
    last_checked: datetime | None = None
    last_healthy: datetime | None = None


class SystemHealth(BaseModel):
    services: list[ServiceHealth]
    overall: ServiceStatus
