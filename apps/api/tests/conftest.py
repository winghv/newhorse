"""
Shared test fixtures — in-memory SQLite + httpx test client.
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Override DB before any app imports
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["PROJECTS_ROOT"] = "/tmp/newhorse-test-projects"
os.environ["AGENTS_ROOT"] = "/tmp/newhorse-test-agents"
os.environ["THS_TIER"] = "test"

# Import the db module so we can replace engine / SessionLocal
import app.db.base as db_base
from app.db.base import Base

# Replace the module-level engine with one that uses StaticPool so that
# every connection (including the on_startup handler and seed_providers)
# shares the same in-memory SQLite database.
_test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
db_base.engine = _test_engine
db_base.SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=_test_engine,
)

# Now import the rest — they will pick up the patched engine / SessionLocal
import app.db as db_pkg          # noqa: E402
db_pkg.engine = _test_engine     # also patch the re-export

from app.db import get_db        # noqa: E402
from app.main import app         # noqa: E402

# Patch the engine reference that migrate.py captured at import time
import app.db.migrate as migrate_mod  # noqa: E402
migrate_mod.engine = _test_engine


@pytest.fixture()
def db_session():
    """Create a fresh in-memory SQLite DB for each test."""
    Base.metadata.create_all(bind=_test_engine)
    TestingSession = sessionmaker(bind=_test_engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        # Drop all data between tests so each test starts clean
        Base.metadata.drop_all(bind=_test_engine)
        Base.metadata.create_all(bind=_test_engine)


@pytest.fixture()
def client(db_session):
    """httpx-compatible test client with overridden DB dependency."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def sample_project(client):
    """Create and return a sample project via API."""
    resp = client.post("/api/projects/", json={
        "name": "Test Project",
        "description": "A test project",
    })
    assert resp.status_code == 200
    return resp.json()


@pytest.fixture()
def sample_provider(db_session):
    """Create a sample provider in the DB."""
    from app.models.provider import Provider
    provider = Provider(
        id="test-provider",
        name="Test Provider",
        provider_type="anthropic",
        api_key="test-key",
        is_active=True,
    )
    db_session.add(provider)
    db_session.commit()
    return provider


@pytest.fixture()
def sample_message(db_session, sample_project):
    """Create a sample message in the DB."""
    from app.models.messages import Message
    import uuid
    message = Message(
        id=str(uuid.uuid4()),
        project_id=sample_project["id"],
        role="user",
        message_type="chat",
        content="Hello world",
    )
    db_session.add(message)
    db_session.commit()
    return message
