from contextvars import ContextVar
from dataclasses import dataclass, field

from starlette.types import ASGIApp, Receive, Scope, Send

from media_manager.auth.db import User

_USER_AGENT_MAX_LENGTH = 512


@dataclass
class AuditContext:
    """Who is making the current request, and from where."""

    ip_address: str | None = None
    user_agent: str | None = None
    actor: User | None = field(default=None)


_audit_context: ContextVar[AuditContext | None] = ContextVar(
    "audit_context", default=None
)


def get_audit_context() -> AuditContext | None:
    return _audit_context.get()


def set_audit_actor(user: User) -> None:
    """Called by the current-user dependencies once a request is authenticated."""
    context = _audit_context.get()
    if context is not None:
        context.actor = user


def audit_context_from_scope(scope: Scope) -> AuditContext:
    client = scope.get("client")
    user_agent = None
    for name, value in scope.get("headers", []):
        if name == b"user-agent":
            user_agent = value.decode("latin-1")[:_USER_AGENT_MAX_LENGTH]
            break
    return AuditContext(ip_address=client[0] if client else None, user_agent=user_agent)


class AuditContextMiddleware:
    """
    Starts a fresh audit context for every HTTP request. Must run inside
    ProxyHeadersMiddleware (i.e. be added before it), so that the client
    address is the forwarded one.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = _audit_context.set(audit_context_from_scope(scope))
        try:
            await self.app(scope, receive, send)
        finally:
            _audit_context.reset(token)
