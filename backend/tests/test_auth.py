from sqlalchemy import select

from app.models import AuditLog, User
from tests.conftest import PW, login

API = "/api/v1"


def test_login_success_and_me(client, auth):
    r = client.get(f"{API}/users/me", headers=auth("SA1"))
    assert r.status_code == 200 and r.json()["role"] == "super_admin"
    assert "users.manage" in r.json()["permissions"]
    assert "password_hash" not in r.text


def test_invalid_login_generic_message(client):
    a = login(client, "SA1", "wrong-password-1A")
    b = login(client, "NOPE", "wrong-password-1A")
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_deactivated_account_cannot_login_and_token_dies(client, auth, db):
    h = auth("OP1")
    assert client.get(f"{API}/users/me", headers=h).status_code == 200
    db.scalar(select(User).where(User.employee_id == "OP1")).is_active = False
    db.commit()
    assert client.get(f"{API}/users/me", headers=h).status_code == 401
    assert login(client, "OP1").status_code == 401


def test_unauthenticated_and_garbage_token(client):
    assert client.get(f"{API}/users/me").status_code == 401
    assert client.get(f"{API}/users", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_lockout_after_repeated_failures(client):
    for _ in range(5):
        login(client, "WO1", "bad-password-1A")
    assert login(client, "WO1").status_code == 429  # even the correct password


def test_logout_revokes_session(client, auth):
    h = auth("MA1")
    assert client.post(f"{API}/auth/logout", headers=h).status_code == 204
    assert client.get(f"{API}/users/me", headers=h).status_code == 401


def test_refresh_rotation_single_use(client):
    t = login(client, "WO1").json()
    r1 = client.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r1.status_code == 200
    assert client.post(f"{API}/auth/refresh", json={"refresh_token": t["refresh_token"]}).status_code == 401


def test_forgot_password_does_not_reveal_accounts(client):
    a = client.post(f"{API}/auth/forgot-password", json={"employee_id": "SA1"})
    b = client.post(f"{API}/auth/forgot-password", json={"employee_id": "ghost"})
    assert a.status_code == b.status_code == 202 and a.json() == b.json()


def test_login_events_audited(client, db):
    login(client, "SA1")
    login(client, "SA1", "bad-password-1A")
    actions = {a.action for a in db.scalars(select(AuditLog))}
    assert {"login.success", "login.failed"} <= actions


def test_audit_log_is_append_only(db):
    import pytest
    row = AuditLog(action="x")
    db.add(row)
    db.commit()
    row.action = "tampered"
    with pytest.raises(PermissionError):
        db.commit()
    db.rollback()
