"""Tests for gateway FastAPI app."""

from fastapi.testclient import TestClient

from gateway.app import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert "checks" in data


def test_api_strategies():
    r = client.get("/api/strategies")
    assert r.status_code == 200
    data = r.json()
    assert "strategies" in data
    assert len(data["strategies"]) >= 1
