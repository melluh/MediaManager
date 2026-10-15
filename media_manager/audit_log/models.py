import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from media_manager.database import Base


class AuditLog(Base):
    """
    One action a user took. The user and subject ids deliberately aren't
    foreign keys: an entry must outlive the user or media it is about, which
    is also why their names are stored as labels at the time of the action.
    """

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True, default=None)
    actor_label: Mapped[str | None] = mapped_column(String(320), default=None)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(index=True, default=None)
    """The user the action was done to, e.g. by an admin."""
    subject_type: Mapped[str | None] = mapped_column(String(32), default=None)
    subject_id: Mapped[str | None] = mapped_column(String(64), default=None)
    subject_label: Mapped[str | None] = mapped_column(String(512), default=None)
    details = mapped_column(JSONB, nullable=False, server_default="{}")
    ip_address: Mapped[str | None] = mapped_column(String(45), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(512), default=None)
