"""
Level 1 integration tests.
Tests the /health endpoint using FastAPI TestClient (no external services needed
for the test runner itself; mocks are used for DB and Redis).
"""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture()
def client():
    """Return a synchronous TestClient wrapping the FastAPI app."""
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── /api/v1/health ────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Tests for GET /api/v1/health"""

    def test_health_returns_200(self, client):
        """Health endpoint must always return HTTP 200."""
        with (
            patch("app.api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("app.api.routes.health.check_redis_connection", new_callable=AsyncMock, return_value=True),
        ):
            response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_ok_when_all_services_up(self, client):
        """status == 'ok' when both DB and Redis are healthy."""
        with (
            patch("app.api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("app.api.routes.health.check_redis_connection", new_callable=AsyncMock, return_value=True),
        ):
            data = client.get("/api/v1/health").json()

        assert data["status"] == "ok"
        assert data["services"]["database"]["status"] == "ok"
        assert data["services"]["redis"]["status"] == "ok"

    def test_health_degraded_when_db_down(self, client):
        """status == 'degraded' when DB is unreachable."""
        with (
            patch("app.api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=False),
            patch("app.api.routes.health.check_redis_connection", new_callable=AsyncMock, return_value=True),
        ):
            data = client.get("/api/v1/health").json()

        assert data["status"] == "degraded"
        assert data["services"]["database"]["status"] == "error"
        assert data["services"]["redis"]["status"] == "ok"

    def test_health_degraded_when_redis_down(self, client):
        """status == 'degraded' when Redis is unreachable."""
        with (
            patch("app.api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("app.api.routes.health.check_redis_connection", new_callable=AsyncMock, return_value=False),
        ):
            data = client.get("/api/v1/health").json()

        assert data["status"] == "degraded"
        assert data["services"]["redis"]["status"] == "error"

    def test_health_response_has_version(self, client):
        """Response must include a version field."""
        with (
            patch("app.api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("app.api.routes.health.check_redis_connection", new_callable=AsyncMock, return_value=True),
        ):
            data = client.get("/api/v1/health").json()
        assert "version" in data
        assert data["version"] != ""

    def test_health_latency_present(self, client):
        """Each service entry must expose a latency_ms value."""
        with (
            patch("app.api.routes.health.check_db_connection", new_callable=AsyncMock, return_value=True),
            patch("app.api.routes.health.check_redis_connection", new_callable=AsyncMock, return_value=True),
        ):
            data = client.get("/api/v1/health").json()

        assert "latency_ms" in data["services"]["database"]
        assert "latency_ms" in data["services"]["redis"]


# ── Root endpoint ─────────────────────────────────────────────────────────────

class TestRootEndpoint:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_contains_message(self, client):
        data = client.get("/").json()
        assert "message" in data
