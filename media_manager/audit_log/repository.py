import uuid

from sqlalchemy import ColumnElement, String, and_, case, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from media_manager.audit_log.models import AuditLog
from media_manager.audit_log.schemas import AuditAction, AuditLogEntry
from media_manager.auth.db import User
from media_manager.movies.models import Movie
from media_manager.tv.models import Show

# The movie or show an entry is about: its subject, or for a download, the
# media the download is for.
_is_media_subject = AuditLog.subject_type.in_(["movie", "show"])
_media_type = case(
    (_is_media_subject, AuditLog.subject_type),
    else_=AuditLog.details["media_type"].astext,
)
_media_id = case(
    (_is_media_subject, AuditLog.subject_id),
    else_=AuditLog.details["media_id"].astext,
)


class AuditLogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, entry: AuditLog) -> None:
        self.db.add(entry)
        await self.db.flush()

    @staticmethod
    def _filters(
        user_id: uuid.UUID | None, actions: list[AuditAction] | None
    ) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = []
        if user_id is not None:
            filters.append(
                or_(
                    AuditLog.actor_user_id == user_id,
                    AuditLog.target_user_id == user_id,
                )
            )
        if actions is not None:
            filters.append(AuditLog.action.in_([str(action) for action in actions]))
        return filters

    async def list_entries(
        self,
        *,
        user_id: uuid.UUID | None,
        actions: list[AuditAction] | None,
        limit: int,
        offset: int,
    ) -> list[AuditLogEntry]:
        stmt = (
            select(
                AuditLog,
                User.display_name,
                User.email,
                User.is_superuser,
                func.coalesce(Movie.slug, Show.slug),
            )
            .outerjoin(User, User.id == AuditLog.actor_user_id)
            .outerjoin(
                Movie,
                and_(_media_type == "movie", cast(Movie.id, String) == _media_id),
            )
            .outerjoin(
                Show,
                and_(_media_type == "show", cast(Show.id, String) == _media_id),
            )
            .where(*self._filters(user_id, actions))
            .order_by(AuditLog.timestamp.desc(), AuditLog.id)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            AuditLogEntry(
                id=entry.id,
                timestamp=entry.timestamp,
                action=AuditAction(entry.action),
                actor_user_id=entry.actor_user_id,
                actor_label=display_name or email or entry.actor_label,
                actor_is_admin=is_superuser,
                target_user_id=entry.target_user_id,
                subject_type=entry.subject_type,
                subject_id=entry.subject_id,
                subject_label=entry.subject_label,
                media_slug=media_slug,
                details=entry.details,
                ip_address=entry.ip_address,
                user_agent=entry.user_agent,
            )
            for entry, display_name, email, is_superuser, media_slug in rows
        ]

    async def count_entries(
        self, *, user_id: uuid.UUID | None, actions: list[AuditAction] | None
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(*self._filters(user_id, actions))
        )
        return (await self.db.execute(stmt)).scalar_one()
