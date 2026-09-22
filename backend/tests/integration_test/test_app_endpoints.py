from unittest.mock import patch

from fastapi.testclient import TestClient


def test_health_endpoint_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"


def test_lifespan_seeds_db_when_seed_on_startup_is_enabled():
    from app.main import app

    with (
        patch("app.main.init_db") as mock_init_db,
        patch("app.main.seed_db") as mock_seed_db,
        patch("app.main.settings.seed_on_startup", True),
        TestClient(app),
    ):
        mock_init_db.assert_called_once()
        mock_seed_db.assert_called_once()


def test_lifespan_skips_seed_when_seed_on_startup_is_disabled():
    from app.main import app

    with (
        patch("app.main.init_db") as mock_init_db,
        patch("app.main.seed_db") as mock_seed_db,
        patch("app.main.settings.seed_on_startup", False),
        TestClient(app),
    ):
        mock_init_db.assert_called_once()
        mock_seed_db.assert_not_called()
