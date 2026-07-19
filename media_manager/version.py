import logging
import os
import re

import httpx
from pydantic import BaseModel

log = logging.getLogger(__name__)

GITHUB_RELEASES_URL = "https://api.github.com/repos/maxdorninger/mediamanager/releases"

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


class HealthResponse(BaseModel):
    message: str
    version: str
    latest_version: str | None = None
    update_available: bool = False


def _parse_semver(value: str) -> tuple[int, int, int] | None:
    match = _SEMVER_RE.match(value.lstrip("v"))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


class VersionChecker:
    def __init__(self) -> None:
        self.current_version = os.getenv("PUBLIC_VERSION", "dev")
        self.latest_version: str | None = None
        self.update_available: bool = False

    @property
    def is_dev(self) -> bool:
        return self.current_version == "locally-built" or self.current_version.startswith("dev")

    async def check_for_update(self) -> None:
        if self.is_dev:
            return

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(GITHUB_RELEASES_URL)
                response.raise_for_status()
                releases = response.json()
            latest_version = str(releases[0]["tag_name"]).lstrip("v")
        except Exception:
            log.exception("Failed to check for MediaManager updates")
            return

        current_parsed = _parse_semver(self.current_version)
        latest_parsed = _parse_semver(latest_version)

        self.latest_version = latest_version
        self.update_available = latest_parsed is not None and (
            current_parsed is None or latest_parsed > current_parsed
        )

        if self.update_available:
            log.warning(
                f"A new version of MediaManager is available: {latest_version} "
                f"(currently running {self.current_version})"
            )


_version_checker: VersionChecker | None = None


def get_version_checker() -> VersionChecker:
    global _version_checker
    if _version_checker is None:
        _version_checker = VersionChecker()
    return _version_checker
