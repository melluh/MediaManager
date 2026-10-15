import uuid
from types import SimpleNamespace

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from media_manager.audit_log.context import (
    AuditContextMiddleware,
    audit_context_from_scope,
    get_audit_context,
)
from media_manager.audit_log.schemas import AuditAction, actions_in_category
from media_manager.audit_log.service import user_update_audit_events
from media_manager.auth import users


def _before(**overrides: object) -> dict[str, object]:
    return {
        "email": "bob@example.com",
        "display_name": "Bob",
        "is_superuser": False,
        "is_active": True,
        "is_verified": True,
        **overrides,
    }


def test_own_detail_changes_are_one_account_update():
    events = user_update_audit_events(
        _before(),
        {"display_name": "Robert", "email": "bob@example.com"},
        is_self=True,
    )

    assert events == [
        (
            AuditAction.account_updated,
            {"changes": {"display_name": {"from": "Bob", "to": "Robert"}}},
        )
    ]


def test_admin_edit_records_details_and_role_change_separately():
    events = user_update_audit_events(
        _before(),
        {"display_name": "Robert", "is_superuser": True},
        is_self=False,
    )

    assert [action for action, _ in events] == [
        AuditAction.user_updated,
        AuditAction.user_promoted,
    ]


def test_status_changes():
    def actions(before: dict[str, object], update: dict[str, object]) -> list:
        return [a for a, _ in user_update_audit_events(before, update, is_self=False)]

    assert actions(_before(is_superuser=True), {"is_superuser": False}) == [
        AuditAction.user_demoted
    ]
    assert actions(_before(), {"is_active": False}) == [AuditAction.user_deactivated]
    assert actions(_before(is_active=False), {"is_active": True}) == [
        AuditAction.user_reactivated
    ]
    assert actions(_before(is_verified=False), {"is_verified": True}) == [
        AuditAction.user_approved
    ]


def test_unverifying_is_recorded_as_a_change():
    events = user_update_audit_events(_before(), {"is_verified": False}, is_self=False)

    assert events == [
        (
            AuditAction.user_updated,
            {"changes": {"is_verified": {"from": True, "to": False}}},
        )
    ]


def test_password_changes_never_include_the_password():
    own = user_update_audit_events(_before(), {"password": "hunter2"}, is_self=True)
    other = user_update_audit_events(_before(), {"password": "hunter2"}, is_self=False)

    assert own == [(AuditAction.account_password_changed, {})]
    assert other == [(AuditAction.user_password_set, {})]
    assert "hunter2" not in repr(own + other)


def test_an_update_that_changes_nothing_records_nothing():
    assert user_update_audit_events(_before(), _before(), is_self=False) == []


def test_categories_partition_all_actions():
    categories = ["auth", "account", "user", "media", "download"]
    grouped = [action for c in categories for action in actions_in_category(c)]

    assert sorted(grouped) == sorted(AuditAction)
    assert AuditAction.user_promoted in actions_in_category("user")
    assert AuditAction.account_updated not in actions_in_category("user")


def test_context_from_scope_reads_client_and_truncated_user_agent():
    context = audit_context_from_scope(
        {
            "type": "http",
            "client": ("203.0.113.4", 1234),
            "headers": [(b"user-agent", b"x" * 1000)],
        }
    )

    assert context.ip_address == "203.0.113.4"
    assert context.user_agent == "x" * 512
    assert context.actor is None


def test_actor_and_client_reach_the_endpoint():
    user = SimpleNamespace(id=uuid.uuid4(), email="bob@example.com")
    app = FastAPI()
    app.add_middleware(AuditContextMiddleware)
    app.dependency_overrides[users._current_active_user] = lambda: user

    @app.get("/whoami", dependencies=[Depends(users.current_active_user)])
    async def whoami() -> dict[str, str | None]:
        context = get_audit_context()
        assert context is not None
        assert context.actor is user
        return {"ip": context.ip_address, "ua": context.user_agent}

    response = TestClient(app).get("/whoami", headers={"user-agent": "pytest"})

    assert response.status_code == 200
    assert response.json() == {"ip": "testclient", "ua": "pytest"}
    assert get_audit_context() is None
