import os
from pathlib import Path

import pytest


TEST_DB = Path(".pytest_vision_relevance.db")

os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["APP_ENV"] = "test"
os.environ["VISION_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["DEMO_API_KEY"] = "demo-local-key"


from app.config import get_settings

get_settings.cache_clear()

from app import models  # noqa: E402,F401
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_database():
    TEST_DB.unlink(missing_ok=True)

    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture
def db():
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
