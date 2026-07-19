from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ServiceStatus(str, Enum):
    healthy = "healthy"
    unavailable = "unavailable"
    unknown = "unknown"


class ServiceHealth(BaseModel):
    name: str
    display_name: str
    status: ServiceStatus
    message: str | None = None
    last_checked: datetime | None = None


class SystemHealth(BaseModel):
    services: list[ServiceHealth]
    overall: ServiceStatus
