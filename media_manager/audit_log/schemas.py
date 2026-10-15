import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class AuditAction(StrEnum):
    # Authentication
    login = "auth.login"
    login_failed = "auth.login_failed"
    password_reset_requested = "auth.password_reset_requested"  # noqa: S105
    password_reset = "auth.password_reset"  # noqa: S105
    email_verified = "auth.email_verified"

    # The acting user's own account
    account_registered = "account.registered"
    account_updated = "account.updated"
    account_password_changed = "account.password_changed"  # noqa: S105
    account_oauth_linked = "account.oauth_linked"

    # Admins managing other users
    user_created = "user.created"
    user_updated = "user.updated"
    user_promoted = "user.promoted"
    user_demoted = "user.demoted"
    user_deactivated = "user.deactivated"
    user_reactivated = "user.reactivated"
    user_approved = "user.approved"
    user_password_set = "user.password_set"  # noqa: S105
    user_deleted = "user.deleted"
    user_oauth_unlinked = "user.oauth_unlinked"
    user_media_server_linked = "user.media_server_linked"
    user_media_server_unlinked = "user.media_server_unlinked"

    # Movies and shows
    media_added = "media.added"
    media_deleted = "media.deleted"
    media_file_deleted = "media.file_deleted"
    media_library_changed = "media.library_changed"
    media_continuous_download_changed = "media.continuous_download_changed"
    media_metadata_refreshed = "media.metadata_refreshed"
    media_imported = "media.imported"
    media_files_rescanned = "media.files_rescanned"
    media_library_scanned = "media.library_scanned"
    media_torrent_import_resolved = "media.torrent_import_resolved"

    # Downloads
    download_started = "download.started"
    download_cancelled = "download.cancelled"
    download_deleted = "download.deleted"
    download_retried = "download.retried"
    download_status_changed = "download.status_changed"


AuditCategory = Literal["auth", "account", "user", "media", "download"]

AuditSubjectType = Literal["movie", "show", "torrent", "user"]


def actions_in_category(category: AuditCategory) -> list[AuditAction]:
    return [action for action in AuditAction if action.startswith(f"{category}.")]


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timestamp: datetime
    action: AuditAction
    actor_user_id: uuid.UUID | None
    actor_label: str | None
    """The actor's current name, or the one they had at the time if they've
    since been deleted."""
    actor_is_admin: bool | None
    """Whether the actor is currently an admin; None if they've been deleted."""
    target_user_id: uuid.UUID | None
    subject_type: AuditSubjectType | None
    subject_id: str | None
    subject_label: str | None
    media_slug: str | None
    """The current slug of the movie or show the entry is about, directly or
    through a download; None if it has since been deleted."""
    details: dict[str, Any]
    ip_address: str | None
    user_agent: str | None


class AuditLogPage(BaseModel):
    items: list[AuditLogEntry]
    total: int
