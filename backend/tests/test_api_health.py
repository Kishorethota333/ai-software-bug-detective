
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_success():
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert "app" in data
    assert "ai_provider" in data


def test_openapi_documentation_is_available():
    response = client.get("/openapi.json")

    assert response.status_code == 200

    data = response.json()
    assert "paths" in data
    assert "/api/health" in data["paths"]
