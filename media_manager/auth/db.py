import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from fastapi import Depends
from fastapi_users.db import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyUserDatabase,
)
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from media_manager.database import Base, get_async_session


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    access_token: Mapped[str] = mapped_column(String(length=4096), nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(
        String(length=4096), nullable=True
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    """When the account was last used to log in. NULL if it hasn't been since
    this started being tracked."""


class MediaServerAccount(Base):
    """
    Links a MediaManager user to their account on the media server. Only set
    by superusers, since there's no way to verify which media server account
    actually belongs to a user.
    """

    __tablename__ = "media_server_account"
    __table_args__ = (
        UniqueConstraint("user_id", "provider"),
        UniqueConstraint("provider", "external_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(length=100), nullable=False)
    """The media server provider's `name`, e.g. "jellyfin"."""
    external_user_id: Mapped[str] = mapped_column(String(length=255), nullable=False)
    username: Mapped[str] = mapped_column(String(length=320), nullable=False)
    """The account's name on the media server when it was linked, for
    display without a round trip to the server."""


class User(SQLAlchemyBaseUserTableUUID, Base):
    display_name: Mapped[str | None] = mapped_column(String(length=320), nullable=True)
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined", passive_deletes="all"
    )
    media_server_accounts: Mapped[list[MediaServerAccount]] = relationship(
        "MediaServerAccount", lazy="joined", passive_deletes="all"
    )


async def get_user_db(
    session: AsyncSession = Depends(get_async_session),
) -> AsyncGenerator[SQLAlchemyUserDatabase]:
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)
