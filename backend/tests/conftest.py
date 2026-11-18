"""Test setup: runs the real app against a separate PostgreSQL database (daycompass_test).

Locally `docker compose up -d postgres` is enough; CI provides a postgres service. Set
TEST_DATABASE_URL to use another server. Every test registers its own user, so tests do not
depend on each other and the database is simply re-created once per run.
"""
import os
import uuid

import psycopg2
import pytest
from sqlalchemy.engine import make_url

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/daycompass_test"
)
os.environ["DATABASE_URL"] = TEST_URL  # must be set before the app is imported


def _ensure_database() -> None:
    url = make_url(TEST_URL)
    admin = psycopg2.connect(
        dbname="postgres", user=url.username, password=url.password, host=url.host, port=url.port or 5432
    )
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (url.database,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{url.database}"')
    admin.close()


_ensure_database()

from fastapi.testclient import TestClient  # noqa: E402

from app.infrastructure.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.application.services.badges import seed_badges  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _fresh_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_badges(db)
    yield


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db():
    with SessionLocal() as session:
        yield session


class Account:
    """A freshly registered user with ready-made auth headers."""

    def __init__(self, client, name="Tester"):
        self.client = client
        self.email = f"{uuid.uuid4().hex[:10]}@test.io"
        self.password = "pw123456"
        r = client.post("/api/auth/register", json={"name": name, "email": self.email, "password": self.password})
        assert r.status_code == 200, r.text
        self.token = r.json()["token"]
        self.id = r.json()["user"]["id"]
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def get(self, path, **kw):
        return self.client.get(path, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    def post(self, path, **kw):
        return self.client.post(path, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    def put(self, path, **kw):
        return self.client.put(path, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    def delete(self, path, **kw):
        # client.request, because DELETE with a JSON body (delete account) is not supported by client.delete
        return self.client.request("DELETE", path, headers={**self.headers, **kw.pop("headers", {})}, **kw)

    def points(self) -> int:
        return self.get("/api/auth/me").json()["total_points"]


@pytest.fixture()
def user(client):
    return Account(client)


@pytest.fixture()
def other(client):
    return Account(client, name="Other")
