import uuid

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr


class UserRead(schemas.BaseUser[uuid.UUID]):
    username: str | None = None


class UserCreate(schemas.BaseUserCreate):
    username: str | None = None


class UserUpdate(schemas.BaseUserUpdate):
    username: str | None = None


class AdminUserCreate(BaseModel):
    email: EmailStr
    username: str | None = None
    password: str | None = None
    is_superuser: bool = False
    is_verified: bool = True


class AuthMetadata(BaseModel):
    oauth_providers: list[str]
    registration_enabled: bool
    allow_self_account_edit: bool
    allow_self_password_change: bool
