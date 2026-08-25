from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app


@pytest.fixture
def client(db_session: Session, seeded_companies) -> Generator[TestClient, None, None]:
    """API client backed by the in-memory SQLite session."""
    _ = seeded_companies

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with (
        patch("app.main.init_db"),
        patch("app.main.seed_db"),
        TestClient(app) as test_client,
    ):
        yield test_client
    app.dependency_overrides.clear()
