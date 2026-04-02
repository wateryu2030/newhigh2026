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


def test_system_health_detail():
    r = client.get("/api/system/health-detail")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    data = body.get("data") or {}
    assert "status" in data
    assert "celery" in data
    assert data.get("prometheus_metrics_path") == "/metrics"


def test_system_backtest_errors():
    r = client.get("/api/system/backtest-errors?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body.get("ok") is True
    data = body.get("data") or {}
    assert "items" in data
    assert isinstance(data["items"], list)


def test_pipeline_run_requires_login():
    """对外开放流水线：路由已挂载；提交须携带有效 Bearer（与 JWT_AUTH_REQUIRED 无关）。"""
    r = client.post(
        "/api/strategies/pipeline/run",
        json={"mode": "evolve_only", "evolution": {"population_limit": 4}},
    )
    assert r.status_code == 401
    detail = r.json().get("detail", "")
    assert "登录" in detail or "token" in detail.lower()


def test_pipeline_approve_requires_admin():
    """上架写入 strategy_market 仅 admin，viewer/operator 均 403。"""
    from gateway.auth.jwt_auth import create_access_token

    fake_job = "00000000-0000-4000-8000-000000000001"
    for role in ("viewer", "operator"):
        tok = create_access_token(f"u-{role}", extra_claims={"role": role})
        r = client.post(
            f"/api/strategies/pipeline/jobs/{fake_job}/approve",
            headers={"Authorization": f"Bearer {tok}"},
            json={},
        )
        assert r.status_code == 403
        assert "admin" in (r.json().get("detail") or "").lower()
