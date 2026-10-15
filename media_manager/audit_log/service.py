import logging
import uuid
from typing import Any

import media_manager.database
from media_manager.audit_log.context import get_audit_context
from media_manager.audit_log.models import AuditLog
from media_manager.audit_log.repository import AuditLogRepository
from media_manager.audit_log.schemas import (
    AuditAction,
    AuditCategory,
    AuditLogPage,
    AuditSubjectType,
    actions_in_category,
)
from media_manager.auth.db import User
from media_manager.common.schemas import BaseMedia
from media_manager.torrent.schemas import Torrent

log = logging.getLogger(__name__)


def user_label(user: User) -> str:
    return user.display_name or user.email


def media_label(media: BaseMedia) -> str:
    return f"{media.name} ({media.year})" if media.year else media.name


def _build_entry(
    action: AuditAction,
    *,
    actor: User | None,
    subject_type: AuditSubjectType | None,
    subject_id: uuid.UUID | str | None,
    subject_label: str | None,
    target_user_id: uuid.UUID | None,
    details: dict[str, Any] | None,
) -> AuditLog:
    """
    The entry for an action, filling in the actor, IP and user agent from
    the current request. The actor defaults to the request's authenticated
    user; pass one for requests that aren't authenticated yet (logins,
    sign-ups, password resets).
    """
    context = get_audit_context()
    actor = actor or (context.actor if context else None)
    return AuditLog(
        action=str(action),
        actor_user_id=actor.id if actor else None,
        actor_label=user_label(actor) if actor else None,
        target_user_id=target_user_id,
        subject_type=subject_type,
        subject_id=str(subject_id) if subject_id is not None else None,
        subject_label=subject_label,
        details=details or {},
        ip_address=context.ip_address if context else None,
        user_agent=context.user_agent if context else None,
    )


class AuditLogService:
    def __init__(self, repository: AuditLogRepository) -> None:
        self.repository = repository

    async def record(
        self,
        action: AuditAction,
        *,
        actor: User | None = None,
        subject_type: AuditSubjectType | None = None,
        subject_id: uuid.UUID | str | None = None,
        subject_label: str | None = None,
        target_user_id: uuid.UUID | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Records an action in the request's own database session, so that the
        entry is only kept if the action itself is committed.
        """
        await self.repository.add(
            _build_entry(
                action,
                actor=actor,
                subject_type=subject_type,
                subject_id=subject_id,
                subject_label=subject_label,
                target_user_id=target_user_id,
                details=details,
            )
        )

    async def record_media(
        self,
        action: AuditAction,
        media: BaseMedia,
        media_type: AuditSubjectType,
        details: dict[str, Any] | None = None,
    ) -> None:
        await self.record(
            action,
            subject_type=media_type,
            subject_id=media.id,
            subject_label=media_label(media),
            details=details,
        )

    async def record_for_user(
        self,
        action: AuditAction,
        user: User,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Records an action done to `user`, e.g. by an admin."""
        await self.record(
            action,
            subject_type="user",
            subject_id=user.id,
            subject_label=user_label(user),
            target_user_id=user.id,
            details=details,
        )

    async def get_entries(
        self,
        *,
        user_id: uuid.UUID | None,
        category: AuditCategory | None,
        action: AuditAction | None,
        limit: int,
        offset: int,
    ) -> AuditLogPage:
        actions = None
        if category is not None:
            actions = actions_in_category(category)
        if action is not None:
            actions = [a for a in actions or [action] if a == action]
        return AuditLogPage(
            items=await self.repository.list_entries(
                user_id=user_id, actions=actions, limit=limit, offset=offset
            ),
            total=await self.repository.count_entries(user_id=user_id, actions=actions),
        )


async def record_detached(
    action: AuditAction,
    *,
    target_user: User | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Records an action in a session of its own, committed immediately. For
    actions that are recorded on a request that then fails (e.g. a failed
    login), whose own session is rolled back.
    """
    if media_manager.database.SessionLocal is None:
        return
    entry = _build_entry(
        action,
        actor=None,
        subject_type="user" if target_user else None,
        subject_id=target_user.id if target_user else None,
        subject_label=user_label(target_user) if target_user else None,
        target_user_id=target_user.id if target_user else None,
        details=details,
    )
    try:
        async with media_manager.database.SessionLocal() as session:
            session.add(entry)
            await session.commit()
    except Exception:
        log.exception(f"Failed to record audit log entry {action}")


USER_SNAPSHOT_FIELDS = (
    "email",
    "display_name",
    "is_superuser",
    "is_active",
    "is_verified",
)

_FLAG_EVENTS: dict[str, tuple[AuditAction, AuditAction | None]] = {
    # field: (action when it becomes true, action when it becomes false)
    "is_superuser": (AuditAction.user_promoted, AuditAction.user_demoted),
    "is_active": (AuditAction.user_reactivated, AuditAction.user_deactivated),
    "is_verified": (AuditAction.user_approved, None),
}


def user_snapshot(user: User) -> dict[str, Any]:
    return {field: getattr(user, field) for field in USER_SNAPSHOT_FIELDS}


def user_update_audit_events(
    before: dict[str, Any], update: dict[str, Any], *, is_self: bool
) -> list[tuple[AuditAction, dict[str, Any]]]:
    """
    The audit log entries for applying `update` to a user who looked like
    `before` (see `user_snapshot`): one for the changed details, plus one per
    role/status change and password change. Never includes the password.
    """
    changes = {
        field: {"from": before[field], "to": update[field]}
        for field in ("email", "display_name")
        if field in update and update[field] != before[field]
    }
    events: list[tuple[AuditAction, dict[str, Any]]] = []
    for field, (became_true, became_false) in _FLAG_EVENTS.items():
        value = update.get(field)
        if value is None or value == before[field]:
            continue
        action = became_true if value else became_false
        if action is None:
            changes[field] = {"from": before[field], "to": value}
        else:
            events.append((action, {}))
    if changes:
        action = AuditAction.account_updated if is_self else AuditAction.user_updated
        events.insert(0, (action, {"changes": changes}))
    if update.get("password") is not None:
        events.append(
            (
                AuditAction.account_password_changed
                if is_self
                else AuditAction.user_password_set,
                {},
            )
        )
    return events


def torrent_details(torrent: Torrent) -> dict[str, Any]:
    return {
        "torrent_id": str(torrent.id),
        "torrent_title": torrent.title,
        "indexer": torrent.indexer,
        "usenet": torrent.usenet,
        "slot": torrent.slot,
    }
