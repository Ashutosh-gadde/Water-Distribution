import os

os.environ["SECRET_KEY"] = "test-only-secret-not-for-production-0123456789"
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import User, Ward

PW = "Correct-Horse-9battery"


@pytest.fixture()
def db():
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(eng)
    S = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    with S() as s:
        for emp, role in [("SA1", "super_admin"), ("MA1", "municipal_admin"), ("WO1", "water_officer"),
                          ("WD1", "ward_officer"), ("OP1", "valve_operator")]:
            s.add(User(employee_id=emp, full_name=f"Demo {emp}", role=role,
                       password_hash=hash_password(PW), is_demo=True))
        s.add_all([Ward(code="D1", name_en="Demo Ward 1", is_demo=True),
                   Ward(code="D2", name_en="Demo Ward 2", is_demo=True)])
        s.commit()
        app.dependency_overrides[get_db] = lambda: s
        yield s
    app.dependency_overrides.clear()


@pytest.fixture()
def client(db):
    return TestClient(app)


def login(client, emp, pw=PW):
    return client.post("/api/v1/auth/login", json={"employee_id": emp, "password": pw})


@pytest.fixture()
def auth(client):
    def _h(emp):
        r = login(client, emp)
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return _h
