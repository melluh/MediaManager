import secrets
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class OpenIdConfig(BaseSettings):
    client_id: str = ""
    client_secret: str = ""
    configuration_endpoint: str = ""
    enabled: bool = False
    name: str = "OAuth2"
    # "never": never sync the display name from the OIDC provider.
    # "if_empty": only sync when the user doesn't have a display name yet
    # (set on account creation, or once for existing users who never set one).
    # "always": overwrite the display name with the OIDC provider's value on every login.
    display_name_sync: Literal["never", "if_empty", "always"] = "never"


class AuthConfig(BaseSettings):
    # to get a signing key run:
    # openssl rand -hex 32
    token_secret: str = Field(default_factory=secrets.token_hex)
    session_lifetime: int = 60 * 60 * 24
    admin_emails: list[str] = []
    email_password_resets: bool = False
    registration_enabled: bool = False
    password_login_enabled: bool = True
    allow_self_account_edit: bool = True
    allow_self_password_change: bool = True
    openid_connect: OpenIdConfig = OpenIdConfig()
