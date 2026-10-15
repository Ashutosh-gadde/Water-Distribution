from tests.conftest import PW

API = "/api/v1"
NEW = {"employee_id": "NEW1", "full_name": "New Person", "role": "valve_operator", "password": PW}


def test_distributor_cannot_manage_users_or_wards(client, auth):
    h = auth("OP1")
    assert client.get(f"{API}/users", headers=h).status_code == 403
    assert client.post(f"{API}/users", json=NEW, headers=h).status_code == 403
    assert client.post(f"{API}/wards", json={"code": "X", "name_en": "X"}, headers=h).status_code == 403


def test_officers_cannot_create_users(client, auth):
    for emp in ("WO1", "WD1"):
        assert client.post(f"{API}/users", json=NEW, headers=auth(emp)).status_code == 403


def test_municipal_admin_cannot_create_equal_or_higher(client, auth):
    h = auth("MA1")
    assert client.post(f"{API}/users", json={**NEW, "role": "super_admin"}, headers=h).status_code == 403
    assert client.post(f"{API}/users", json={**NEW, "role": "municipal_admin"}, headers=h).status_code == 403
    assert client.post(f"{API}/users", json=NEW, headers=h).status_code == 201


def test_municipal_admin_cannot_modify_super_admin(client, auth):
    r = client.patch(f"{API}/users/1", json={"is_active": False}, headers=auth("MA1"))
    assert r.status_code == 403


def test_no_self_escalation_or_self_deactivation(client, auth):
    h = auth("MA1")
    assert client.patch(f"{API}/users/2", json={"role": "super_admin"}, headers=h).status_code == 403
    assert client.patch(f"{API}/users/2", json={"is_active": False}, headers=h).status_code == 403


def test_weak_password_and_duplicate_rejected(client, auth):
    h = auth("SA1")
    assert client.post(f"{API}/users", json={**NEW, "password": "short"}, headers=h).status_code == 422
    assert client.post(f"{API}/users", json=NEW, headers=h).status_code == 201
    assert client.post(f"{API}/users", json=NEW, headers=h).status_code == 409


def test_ward_officer_sees_only_assigned_wards(client, auth):
    sa = auth("SA1")
    assert client.post(f"{API}/users/4/assignments", json={"ward_id": 1}, headers=sa).status_code == 201
    h = auth("WD1")
    ids = [w["id"] for w in client.get(f"{API}/wards", headers=h).json()]
    assert ids == [1]
    assert client.get(f"{API}/wards/1", headers=h).status_code == 200
    assert client.get(f"{API}/wards/2", headers=h).status_code == 403


def test_unassigned_officer_sees_nothing_admin_sees_all(client, auth):
    assert client.get(f"{API}/wards", headers=auth("WD1")).json() == []
    assert len(client.get(f"{API}/wards", headers=auth("MA1")).json()) == 2


def test_assignment_history_preserved_and_access_revoked(client, auth):
    sa = auth("SA1")
    client.post(f"{API}/users/4/assignments", json={"ward_id": 1}, headers=sa)
    assert client.post(f"{API}/users/4/assignments", json={"ward_id": 1}, headers=sa).status_code == 409
    assert client.delete(f"{API}/users/4/assignments/1", headers=sa).status_code == 204
    hist = client.get(f"{API}/users/4/assignments", headers=sa).json()
    assert len(hist) == 1 and hist[0]["ended_at"] is not None
    assert client.get(f"{API}/wards/1", headers=auth("WD1")).status_code == 403


def test_role_change_revokes_sessions(client, auth):
    sa = auth("SA1")
    op = auth("OP1")
    assert client.patch(f"{API}/users/5", json={"role": "ward_officer"}, headers=sa).status_code == 200
    assert client.get(f"{API}/users/me", headers=op).status_code == 401


def test_user_actions_audited(client, auth, db):
    from sqlalchemy import select
    from app.models import AuditLog
    client.post(f"{API}/users", json=NEW, headers=auth("SA1"))
    assert any(a.action == "user.created" for a in db.scalars(select(AuditLog)))


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"
