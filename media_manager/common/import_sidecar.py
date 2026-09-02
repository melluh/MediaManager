import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from media_manager.common.import_match import ImportMatchConfidence
from media_manager.config import get_config
from media_manager.metadataProvider.schemas import MetaDataProviderSearchResult

log = logging.getLogger(__name__)

SIDECAR_FILENAME = ".mediamanager"
SIDECAR_VERSION = 1


class ImportMatchSidecar(BaseModel):
    """
    The resolved match for one importable directory, cached in that directory
    so a rescan doesn't have to search for it again.
    """

    version: int = SIDECAR_VERSION
    directory_name: str
    """The directory name the match was resolved from. A rename changes the
    input to matching, so it invalidates the entry."""
    confidence: ImportMatchConfidence
    match: MetaDataProviderSearchResult | None = None
    resolved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def read_import_sidecar(directory: Path) -> ImportMatchSidecar | None:
    """
    The cached match for a directory, or None when there is nothing usable to
    read. A missing, unreadable, malformed or unknown-version file is a cache
    miss and never an error - the caller simply resolves the directory again.

    :param directory: The scanned directory the sidecar lives in.
    :return: The cached entry, or None.
    """
    path = directory / SIDECAR_FILENAME
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        log.debug(f"Ignoring unreadable import sidecar at {path}", exc_info=True)
        return None

    # Checked before validation so a future format is a plain miss rather than
    # a confusing pile of validation errors.
    if not isinstance(raw, dict) or raw.get("version") != SIDECAR_VERSION:
        log.debug(f"Ignoring import sidecar at {path} with unknown version")
        return None

    try:
        return ImportMatchSidecar.model_validate(raw)
    except ValueError:
        log.debug(f"Ignoring malformed import sidecar at {path}", exc_info=True)
        return None


def write_import_sidecar(directory: Path, sidecar: ImportMatchSidecar) -> bool:
    """
    Caches a resolved match in the directory it belongs to. Strictly
    best-effort: a read-only mount, a permission error or a full disk only
    costs the next scan another lookup, so nothing here is allowed to fail the
    scan or reach the user.

    :param directory: The scanned directory to write the sidecar into.
    :param sidecar: The entry to cache.
    :return: Whether the file was written.
    """
    if not get_config().misc.write_import_sidecars:
        return False
    path = directory / SIDECAR_FILENAME
    try:
        path.write_text(sidecar.model_dump_json(), encoding="utf-8")
    except (OSError, ValueError):
        log.debug(f"Could not write import sidecar at {path}", exc_info=True)
        return False
    return True


def delete_import_sidecar(directory: Path) -> None:
    """
    Removes a directory's cached match, once that directory has been imported
    and belongs to a media item. The scan skips claimed directories, so the
    entry would never be read again - and leaving it behind means leaving a
    stray file in the user's media directory.

    Best-effort, like every other sidecar operation: a missing file or a
    read-only mount is not a problem worth reporting.

    :param directory: The directory whose sidecar should be removed.
    """
    path = directory / SIDECAR_FILENAME
    try:
        path.unlink(missing_ok=True)
    except OSError:
        log.debug(f"Could not remove import sidecar at {path}", exc_info=True)
