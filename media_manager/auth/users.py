import contextlib
import logging
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any, override

from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, exceptions, models
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    CookieTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from httpx_oauth.clients.openid import OpenID
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from starlette import status

import media_manager.notification.utils
from media_manager.audit_log.context import get_audit_context, set_audit_actor
from media_manager.audit_log.repository import AuditLogRepository
from media_manager.audit_log.schemas import AuditAction
from media_manager.audit_log.service import (
    AuditLogService,
    record_detached,
    user_snapshot,
    user_update_audit_events,
)
from media_manager.auth.db import User, get_async_session, get_user_db
from media_manager.auth.schemas import UserCreate, UserUpdate
from media_manager.config import MediaManagerConfig

log = logging.getLogger(__name__)

config = MediaManagerConfig().auth
SECRET = config.token_secret
LIFETIME = config.session_lifetime

openid_client: OpenID | None = None
if config.openid_connect.enabled:
    log.info(f"Configured OIDC provider: {config.openid_connect.name}")
    openid_client = OpenID(
        base_scopes=["openid", "email", "profile"],
        client_id=config.openid_connect.client_id,
        client_secret=config.openid_connect.client_secret,
        name=config.openid_connect.name,
        openid_configuration_endpoint=config.openid_connect.configuration_endpoint,
    )


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    @property
    def audit(self) -> AuditLogService:
        # The user database shares the request's session, so entries are
        # committed (or rolled back) together with the change they describe.
        return AuditLogService(AuditLogRepository(self.user_db.session))

    @override
    async def update(
        self,
        user_update: UserUpdate,
        user: User,
        safe: bool = False,
        request: Request | None = None,
    ) -> User:
        # safe=True is only ever passed by the self-service PATCH /users/me
        # route (admin edits of other users use safe=False), so this scopes
        # the check to users editing their own account.
        if safe and not user.is_superuser:
            changed_fields = user_update.model_dump(exclude_unset=True)
            if "password" in changed_fields and not config.allow_self_password_change:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Changing your own password is disabled. Contact a superuser for assistance.",
                )
            if (
                "email" in changed_fields or "display_name" in changed_fields
            ) and not config.allow_self_account_edit:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Editing your own account details is disabled. Contact a superuser for assistance.",
                )
        before = user_snapshot(user)
        try:
            updated_user = await super().update(
                user_update, user, safe=safe, request=request
            )
        except IntegrityError as e:
            raise exceptions.UserAlreadyExists() from e
        # Updates without a request are internal follow-ups (e.g. re-verifying
        # after an email change), not something a user did.
        if request is not None:
            update_dict = (
                user_update.create_update_dict()
                if safe
                else user_update.create_update_dict_superuser()
            )
            context = get_audit_context()
            is_self = (
                context is None
                or context.actor is None
                or (context.actor.id == updated_user.id)
            )
            for action, details in user_update_audit_events(
                before, update_dict, is_self=is_self
            ):
                await self.audit.record_for_user(action, updated_user, details)
        return updated_user

    @override
    async def authenticate(self, credentials: OAuth2PasswordRequestForm) -> User | None:
        user = await super().authenticate(credentials)
        if user is None:
            try:
                existing_user = await self.get_by_email(credentials.username)
            except exceptions.UserNotExists:
                pass
            else:
                # The login request's session is rolled back when it fails.
                await record_detached(
                    AuditAction.login_failed,
                    target_user=existing_user,
                    details={"email": credentials.username},
                )
        return user

    @override
    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response: Response | None = None,
    ) -> None:
        method = (
            "oidc"
            if request is not None and "/auth/oauth/" in request.url.path
            else "password"
        )
        await self.audit.record(
            AuditAction.login, actor=user, details={"method": method}
        )

    @override
    async def on_after_delete(self, user: User, request: Request | None = None) -> None:
        await self.audit.record_for_user(
            AuditAction.user_deleted,
            user,
            details={
                "email": user.email,
                "display_name": user.display_name,
                "was_pending": not user.is_verified,
            },
        )

    @override
    async def on_before_delete(
        self, user: models.UP, request: Request | None = None
    ) -> None:
        # Unverified users can't sign in, so they can't have created anything
        # yet; rejecting a pending sign-up therefore needs no deactivation first.
        if user.is_active and user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only deactivated or unverified users can be deleted. Deactivate the user first.",
            )

    @override
    async def on_after_update(
        self,
        user: models.UP,
        update_dict: dict[str, Any],
        request: Request | None = None,
    ) -> None:
        log.info(f"User {user.id} has been updated.")
        if update_dict.get("is_superuser"):
            log.info(f"User {user.id} has been granted superuser privileges.")
        if "email" in update_dict:
            updated_user = UserUpdate(is_verified=True)
            await self.update(user=user, user_update=updated_user)

    @override
    async def oauth_callback(
        self,
        oauth_name: str,
        access_token: str,
        account_id: str,
        account_email: str,
        expires_at: int | None = None,
        refresh_token: str | None = None,
        request: Request | None = None,
        *,
        associate_by_email: bool = False,
        is_verified_by_default: bool = False,
    ) -> User:
        # Whether this login links the OAuth account to an existing user by
        # email; logging in with an already linked one or signing up isn't.
        links_existing_user = False
        try:
            await self.get_by_oauth_account(oauth_name, account_id)
        except exceptions.UserNotExists:
            try:
                await self.get_by_email(account_email)
                links_existing_user = associate_by_email
            except exceptions.UserNotExists:
                if not config.registration_enabled:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User registration is disabled.",
                    ) from None
        user = await super().oauth_callback(
            oauth_name,
            access_token,
            account_id,
            account_email,
            expires_at,
            refresh_token,
            request,
            associate_by_email=associate_by_email,
            is_verified_by_default=is_verified_by_default,
        )
        for oauth_account in user.oauth_accounts:
            if (
                oauth_account.oauth_name == oauth_name
                and oauth_account.account_id == account_id
            ):
                user = await self.user_db.update_oauth_account(
                    user, oauth_account, {"last_used_at": datetime.now(UTC)}
                )
                break
        if links_existing_user:
            await self.audit.record(
                AuditAction.account_oauth_linked,
                actor=user,
                subject_type="user",
                subject_id=user.id,
                subject_label=user.display_name or user.email,
                target_user_id=user.id,
                details={"provider": oauth_name, "account_email": account_email},
            )
        return await self._sync_oidc_display_name(user, access_token)

    async def _sync_oidc_display_name(self, user: User, access_token: str) -> User:
        sync_mode = config.openid_connect.display_name_sync
        if sync_mode == "never" or openid_client is None:
            return user
        if sync_mode == "if_empty" and user.display_name:
            return user
        try:
            profile = await openid_client.get_profile(access_token)
            display_name = profile.get("name") or profile.get("preferred_username")
            if display_name:
                display_name = display_name[:320]
            if display_name and display_name != user.display_name:
                user = await self.user_db.update(user, {"display_name": display_name})
        except Exception:
            # Log a warning, but don't let the login fail because of this.
            log.warning(
                f"Could not sync OIDC display name for user {user.id}.", exc_info=True
            )
        return user

    @override
    async def on_after_register(
        self, user: User, request: Request | None = None
    ) -> None:
        log.info(f"User {user.id} has registered.")
        context = get_audit_context()
        # Users created by an admin are recorded by that route instead; ones
        # created outside a request (the default admin) aren't user actions.
        if context is not None and context.actor is None:
            await self.audit.record(
                AuditAction.account_registered,
                actor=user,
                subject_type="user",
                subject_id=user.id,
                subject_label=user.display_name or user.email,
                target_user_id=user.id,
                details={
                    "email": user.email,
                    "display_name": user.display_name,
                    "method": "oidc"
                    if request is not None and "/auth/oauth/" in request.url.path
                    else "password",
                },
            )
        if user.email in config.admin_emails:
            updated_user = UserUpdate(is_superuser=True, is_verified=True)
            await self.update(user=user, user_update=updated_user)

    @override
    async def on_after_forgot_password(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        link = f"{MediaManagerConfig().misc.frontend_url}web/login/reset-password?token={token}"
        log.info(f"User {user.id} has forgot their password. Reset Link: {link}")
        await self.audit.record(
            AuditAction.password_reset_requested,
            actor=user,
            details={"email": user.email},
        )

        if not config.email_password_resets:
            log.info("Email password resets are disabled, not sending email.")
            return

        subject = "MediaManager - Password Reset Request"
        html = f"""\
        <html>
          <body>
            <p>Hi {user.email},
            <br>
            <br>
            if you forgot your password, <a href=\"{link}\">reset you password here</a>.<br>
            If you did not request a password reset, you can ignore this email.</p>
            <br>
            <br>
            If the link does not work, copy the following link into your browser: {link}<br>
          </body>
        </html>
        """
        media_manager.notification.utils.send_email(
            subject=subject, html=html, addressee=user.email
        )
        log.info(f"Sent password reset email to {user.email}")

    @override
    async def on_after_reset_password(
        self, user: User, request: Request | None = None
    ) -> None:
        log.info(f"User {user.id} has reset their password.")
        await self.audit.record(AuditAction.password_reset, actor=user)

    @override
    async def on_after_request_verify(
        self, user: User, token: str, request: Request | None = None
    ) -> None:
        log.info(
            f"Verification requested for user {user.id}. Verification token: {token}"
        )

    @override
    async def on_after_verify(self, user: User, request: Request | None = None) -> None:
        log.info(f"User {user.id} has been verified")
        await self.audit.record(AuditAction.email_verified, actor=user)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
) -> AsyncGenerator[UserManager]:
    yield UserManager(user_db)


get_async_session_context = contextlib.asynccontextmanager(get_async_session)
get_user_db_context = contextlib.asynccontextmanager(get_user_db)
get_user_manager_context = contextlib.asynccontextmanager(get_user_manager)


async def create_default_admin_user() -> None:
    """Create a default admin user if no users exist in the database"""
    try:
        async with (
            get_async_session_context() as session,
            get_user_db_context(session) as user_db,
            get_user_manager_context(user_db) as user_manager,
        ):
            # Check if any users exist
            stmt = select(func.count(User.id))
            result = await session.execute(stmt)
            user_count = result.scalar()
            config = MediaManagerConfig()
            if user_count == 0:
                log.info("No users found in database. Creating default admin user...")

                # Use the first admin email from config, or default
                admin_email = (
                    config.auth.admin_emails[0]
                    if config.auth.admin_emails
                    else "admin@example.com"
                )
                default_password = "admin"  # noqa: S105 # Simple default password

                user_create = UserCreate(
                    email=admin_email,
                    password=default_password,
                    is_superuser=True,
                    is_verified=True,
                )

                user = await user_manager.create(user_create)
                log.info("=" * 60)
                log.info("DEFAULT ADMIN USER CREATED!")
                log.info(f"    Email: {admin_email}")
                log.info(f"    Password: {default_password}")
                log.info(f"    User ID: {user.id}")
                log.info("IMPORTANT: Please change this password after first login!")
                log.info("=" * 60)

            else:
                log.info(
                    f"Found {user_count} existing users. Skipping default user creation."
                )
    except Exception:
        log.exception("Failed to create default admin user")
        log.info(
            "You can create an admin user manually by registering with an email from the admin_emails list in your config."
        )


def get_jwt_strategy() -> JWTStrategy[models.UP, models.ID]:
    return JWTStrategy(secret=SECRET, lifetime_seconds=LIFETIME)


# Non-sensitive, JS-readable cookie mirroring whether a session cookie was just
# set/cleared. The real auth cookie is httponly, so the frontend has no way to
# tell "definitely logged out" from "maybe logged in" without a network round
# trip; this lets it skip that round trip for the definitely-logged-out case.
AUTH_HINT_COOKIE_NAME = "mm_authenticated"


class HintCookieTransport(CookieTransport):
    async def get_login_response(self, token: str) -> Response:
        response = await super().get_login_response(token)
        return self._set_hint_cookie(response)

    async def get_logout_response(self) -> Response:
        response = await super().get_logout_response()
        response.delete_cookie(
            AUTH_HINT_COOKIE_NAME, path=self.cookie_path, domain=self.cookie_domain
        )
        return response

    def _set_hint_cookie(self, response: Response) -> Response:
        response.set_cookie(
            AUTH_HINT_COOKIE_NAME,
            "1",
            max_age=self.cookie_max_age,
            path=self.cookie_path,
            domain=self.cookie_domain,
            secure=self.cookie_secure,
            httponly=False,
            samesite=self.cookie_samesite,
        )
        return response


# needed because the default CookieTransport does not redirect after login,
# thus the user would be stuck on the OAuth Providers "redirecting" page
class RedirectingCookieTransport(HintCookieTransport):
    async def get_login_response(self, token: str) -> Response:
        response = RedirectResponse(
            str(MediaManagerConfig().misc.frontend_url) + "web/dashboard",
            status_code=status.HTTP_302_FOUND,
        )
        response = self._set_login_cookie(response, token)
        return self._set_hint_cookie(response)


bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
cookie_transport = HintCookieTransport(
    cookie_max_age=LIFETIME, cookie_samesite="lax", cookie_secure=False
)
openid_cookie_transport = RedirectingCookieTransport(
    cookie_max_age=LIFETIME, cookie_samesite="lax", cookie_secure=False
)

bearer_auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
cookie_auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)
openid_cookie_auth_backend = AuthenticationBackend(
    name="cookie",
    transport=openid_cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager, [bearer_auth_backend, cookie_auth_backend]
)

_current_active_user = fastapi_users.current_user(active=True, verified=True)
_current_active_user_allow_unverified = fastapi_users.current_user(active=True)
_current_superuser = fastapi_users.current_user(
    active=True, verified=True, superuser=True
)

# These wrap fastapi_users' dependencies to also remember the authenticated
# user as the actor of anything the request records in the audit log.


async def current_active_user(user: User = Depends(_current_active_user)) -> User:
    set_audit_actor(user)
    return user


async def current_active_user_allow_unverified(
    user: User = Depends(_current_active_user_allow_unverified),
) -> User:
    """
    Only for endpoints an unverified user needs in order to learn that they
    are unverified, like GET /users/me. Everything else should use
    current_active_user.
    """
    set_audit_actor(user)
    return user


async def current_superuser(user: User = Depends(_current_superuser)) -> User:
    set_audit_actor(user)
    return user
