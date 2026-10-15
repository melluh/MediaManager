import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from fastapi_users import BaseUserManager, exceptions
from fastapi_users.router import get_oauth_router
from httpx_oauth.oauth2 import OAuth2
from sqlalchemy import delete, select

from media_manager.audit_log.dependencies import audit_log_service_dep
from media_manager.audit_log.schemas import AuditAction
from media_manager.auth.db import MediaServerAccount, OAuthAccount, User
from media_manager.auth.schemas import (
    AdminUserCreate,
    AuthMetadata,
    MediaServerAccountLink,
    MediaServerAccountRead,
    UserCreate,
    UserPermissions,
    UserProfile,
    UserRead,
    UserReadWithPermissions,
)
from media_manager.auth.users import (
    SECRET,
    create_default_admin_user,
    current_active_user,
    current_active_user_allow_unverified,
    current_superuser,
    fastapi_users,
    get_user_manager,
    openid_client,
    openid_cookie_auth_backend,
)
from media_manager.config import MediaManagerConfig
from media_manager.database import DbSessionDependency
from media_manager.mediaServer.router import media_server_provider_dep


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator:
    await create_default_admin_user()
    yield


users_router = APIRouter(lifespan=lifespan)
auth_metadata_router = APIRouter()


def get_openid_router() -> APIRouter:
    if openid_client:
        return get_oauth_router(
            oauth_client=openid_client,
            backend=openid_cookie_auth_backend,
            get_user_manager=fastapi_users.get_user_manager,
            state_secret=SECRET,
            associate_by_email=True,
            is_verified_by_default=True,
            redirect_url=None,
        )
    # this is there, so that the appropriate routes are created even if OIDC is not configured,
    # e.g. for generating the frontend's openapi client
    return get_oauth_router(
        oauth_client=OAuth2(
            client_id="mock",
            client_secret="mock",  # noqa: S106
            authorize_endpoint="https://example.com/authorize",
            access_token_endpoint="https://example.com/token",  # noqa: S106
        ),
        backend=openid_cookie_auth_backend,
        get_user_manager=fastapi_users.get_user_manager,
        state_secret=SECRET,
        associate_by_email=False,
        is_verified_by_default=False,
        redirect_url=None,
    )


auth_config = MediaManagerConfig().auth
openid_config = auth_config.openid_connect


@users_router.get(
    "/users/all",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def get_all_users(db: DbSessionDependency) -> list[UserRead]:
    stmt = select(User)
    result = (await db.execute(stmt)).scalars().unique()
    return [UserRead.model_validate(user) for user in result]


@users_router.get(
    "/users/{user_id}/profile",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_active_user)],
    responses={status.HTTP_404_NOT_FOUND: {"description": "User not found."}},
)
async def get_user_profile(user_id: uuid.UUID, db: DbSessionDependency) -> UserProfile:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserProfile.model_validate(user)


@users_router.post(
    "/users/",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(current_superuser)],
)
async def admin_create_user(
    payload: AdminUserCreate,
    user_manager: Annotated[
        BaseUserManager[User, uuid.UUID], Depends(get_user_manager)
    ],
    audit: audit_log_service_dep,
) -> UserRead:
    password = payload.password or user_manager.password_helper.generate()
    try:
        user = await user_manager.create(
            UserCreate(
                email=payload.email,
                display_name=payload.display_name,
                password=password,
                is_superuser=payload.is_superuser,
                is_verified=payload.is_verified,
            ),
            safe=False,
        )
    except exceptions.UserAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from exc
    except exceptions.InvalidPasswordException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid password: {exc.reason}",
        ) from exc
    await audit.record_for_user(
        AuditAction.user_created,
        user,
        details={
            "email": user.email,
            "display_name": user.display_name,
            "is_superuser": user.is_superuser,
            "is_verified": user.is_verified,
            "password_generated": payload.password is None,
        },
    )
    return UserRead.model_validate(user)


@users_router.delete(
    "/users/{user_id}/oauth-accounts/{oauth_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def unlink_oauth_account(
    user_id: uuid.UUID,
    oauth_account_id: uuid.UUID,
    db: DbSessionDependency,
    audit: audit_log_service_dep,
) -> None:
    stmt = (
        delete(OAuthAccount)
        .where(OAuthAccount.id == oauth_account_id, OAuthAccount.user_id == user_id)
        .returning(OAuthAccount.oauth_name, OAuthAccount.account_email)
    )
    unlinked = (await db.execute(stmt)).one_or_none()
    if unlinked is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked account not found.",
        )
    user = await db.get(User, user_id)
    if user is not None:
        await audit.record_for_user(
            AuditAction.user_oauth_unlinked,
            user,
            details={
                "provider": unlinked.oauth_name,
                "account_email": unlinked.account_email,
            },
        )


@users_router.put(
    "/users/{user_id}/media-server-account",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(current_superuser)],
)
async def link_media_server_account(
    user_id: uuid.UUID,
    payload: MediaServerAccountLink,
    db: DbSessionDependency,
    provider: media_server_provider_dep,
    audit: audit_log_service_dep,
) -> MediaServerAccountRead:
    """
    Link a user to an account on the configured media server, replacing any
    account they were linked to before. Only superusers can do this, since
    there's no way to verify which account actually belongs to a user.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    try:
        server_user = await provider.get_user(payload.external_user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not fetch the account from {provider.display_name}.",
        ) from exc
    if server_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No such {provider.display_name} account.",
        )

    accounts = (
        await db.execute(
            select(MediaServerAccount).where(
                MediaServerAccount.provider == provider.name,
                (MediaServerAccount.user_id == user_id)
                | (MediaServerAccount.external_user_id == server_user.id),
            )
        )
    ).scalars()
    account = None
    for existing in accounts:
        if existing.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"This {provider.display_name} account is already linked "
                "to another user.",
            )
        account = existing
    if account is None:
        account = MediaServerAccount(user_id=user_id, provider=provider.name)
        db.add(account)
    account.external_user_id = server_user.id
    account.username = server_user.name
    await db.flush()
    await audit.record_for_user(
        AuditAction.user_media_server_linked,
        user,
        details={"provider": provider.display_name, "username": server_user.name},
    )
    return MediaServerAccountRead.model_validate(account)


@users_router.delete(
    "/users/{user_id}/media-server-account",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(current_superuser)],
)
async def unlink_media_server_account(
    user_id: uuid.UUID,
    db: DbSessionDependency,
    provider: media_server_provider_dep,
    audit: audit_log_service_dep,
) -> None:
    stmt = (
        delete(MediaServerAccount)
        .where(
            MediaServerAccount.user_id == user_id,
            MediaServerAccount.provider == provider.name,
        )
        .returning(MediaServerAccount.username)
    )
    unlinked = (await db.execute(stmt)).one_or_none()
    if unlinked is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Linked account not found.",
        )
    user = await db.get(User, user_id)
    if user is not None:
        await audit.record_for_user(
            AuditAction.user_media_server_unlinked,
            user,
            details={"provider": provider.display_name, "username": unlinked.username},
        )


@auth_metadata_router.get("/auth/metadata", status_code=status.HTTP_200_OK)
def get_auth_metadata() -> AuthMetadata:
    providers = [openid_config.name] if openid_config.enabled else []
    return AuthMetadata(
        oauth_providers=providers,
        registration_enabled=auth_config.registration_enabled
        and auth_config.password_login_enabled,
        password_login_enabled=auth_config.password_login_enabled,
    )


# Overrides fastapi_users' generic GET /users/me route (registered further below)
# so we can additionally report the caller's own edit permissions. These depend
# on both instance config and superuser status, so they belong on the
# authenticated user resource rather than on the public /auth/metadata endpoint.
@users_router.get(
    "/users/me",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Missing token or inactive user.",
        },
    },
)
async def get_current_user(
    user: Annotated[User, Depends(current_active_user_allow_unverified)],
) -> UserReadWithPermissions:
    permissions = UserPermissions(
        can_edit_account=user.is_superuser or auth_config.allow_self_account_edit,
        can_change_password=user.is_superuser or auth_config.allow_self_password_change,
    )
    return UserReadWithPermissions(
        **UserRead.model_validate(user).model_dump(), permissions=permissions
    )
