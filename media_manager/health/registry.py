import threading
from datetime import UTC, datetime

from media_manager.health.schemas import ServiceHealth, ServiceStatus, SystemHealth

_registry: "HealthRegistry | None" = None
_registry_lock = threading.Lock()


class HealthRegistry:
    def __init__(self) -> None:
        self._services: dict[str, ServiceHealth] = {}
        self._lock = threading.Lock()

    def update(
        self,
        key: str,
        display_name: str,
        status: ServiceStatus,
        message: str | None = None,
    ) -> None:
        now = datetime.now(UTC)
        with self._lock:
            previous = self._services.get(key)
            last_healthy = previous.last_healthy if previous else None
            if status == ServiceStatus.healthy:
                last_healthy = now
            entry = ServiceHealth(
                name=key,
                display_name=display_name,
                status=status,
                message=message,
                last_checked=now,
                last_healthy=last_healthy,
            )
            self._services[key] = entry

    def get_all(self) -> SystemHealth:
        with self._lock:
            services = list(self._services.values())
        if not services:
            overall = ServiceStatus.unknown
        elif all(s.status == ServiceStatus.healthy for s in services):
            overall = ServiceStatus.healthy
        else:
            overall = ServiceStatus.unavailable
        return SystemHealth(services=services, overall=overall)


def get_health_registry() -> HealthRegistry:
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = HealthRegistry()
    return _registry
