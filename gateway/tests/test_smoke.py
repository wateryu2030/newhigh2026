"""端到端烟雾测试：验证 Gateway 能在无真实 DB 情况下启动并返回结构化响应。

测试策略：
- 使用 FastAPI TestClient（不启动 uvicorn，纯 in-process）
- Mock DuckDB 文件检测（os.path.isfile → False）让所有 DB 查询优雅降级
- 不 mock 外部 HTTP 调用（如 akshare 新闻、Binance K 线等），让它们自然执行，
  但断言该类 endpoint 即使无本地数据也应返回 200 + 合理空结构
- 断言状态码为 200 或合理的 4xx（非 500/崩溃）
- 断言返回体为 dict 或 list（非 None/异常）
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ── 在所有 gateway 导入前设置 JWT 密钥（与根 conftest.py 一致） ──
os.environ.setdefault("JWT_SECRET_KEY", "pytest-jwt-secret-key-ci-only")
os.environ.setdefault("JWT_SECRET", "pytest-jwt-secret-key-ci-only")


@pytest.fixture(scope="module")
def client() -> TestClient:
    """返回一个轻量 TestClient，不启动真实 HTTP 服务器。"""
    from gateway.app import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _no_db_file() -> None:
    """让所有 DuckDB 文件检测均返回「文件不存在」，
    确保 endpoint 内部以空数据/降级状态优雅返回，而非尝试真实连接。"""
    patcher = patch("os.path.isfile", return_value=False)
    patcher.start()
    yield
    patcher.stop()


# ── 1. 基础健康检查 ──


def test_health_root(client: TestClient) -> None:
    """GET /health 应返回 200 + status/checks 等结构化字段。"""
    r = client.get("/health")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict), f"响应应为 dict，实际 {type(data)}"
    assert "status" in data, f"缺少 status 字段: {list(data.keys())}"
    assert data["status"] in (
        "ok",
        "degraded",
    ), f"status 应为 ok 或 degraded，实际 {data['status']}"
    assert "checks" in data, f"缺少 checks 字段"
    assert "timestamp" in data, f"缺少 timestamp 字段"


def test_health_api(client: TestClient) -> None:
    """GET /api/health 应与 /health 等价（监控与 JWT 白名单统一路径）。"""
    r = client.get("/api/health")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    assert "status" in data
    assert "checks" in data


# ── 2. 系统状态 ──


def test_system_status(client: TestClient) -> None:
    """GET /api/system/status 应返回 200 + 各组件 idle 状态。"""
    r = client.get("/api/system/status")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    # 即使无 DB，也应返回完整的 idle 占位结构
    for key in ("data_pipeline", "scanner", "ai_models", "strategy_engine"):
        assert key in data, f"缺少组件状态字段: {key}"
        assert data[key] in (
            "idle",
            "running",
            "error",
        ), f"{key} 状态异常: {data[key]}"


def test_system_health_detail(client: TestClient) -> None:
    """GET /api/system/health-detail 应返回 200 + 丰富健康数据。"""
    r = client.get("/api/system/health-detail")
    # 注意：health-detail 在 import/DB 失败时可能返回 503 (json_fail)
    # 但我们 mock 了 os.path.isfile → False，build_health_payload 应返回 degraded 而非 crash
    assert r.status_code in (
        200,
        503,
    ), f"期望 200/503，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    if r.status_code == 200:
        assert data.get("ok") is True
        inner = data.get("data") or {}
        assert "status" in inner, f"health-detail data 缺少 status"
        assert "celery" in inner, f"health-detail data 缺少 celery"
        # degraded 是因为无 DB 文件
        assert inner["status"] == "degraded", f"期望 degraded，实际 {inner['status']}"


# ── 3. 市场实时行情（DuckDB 依赖） ──


def test_market_realtime(client: TestClient) -> None:
    """GET /api/market/realtime 无 DB 时应返回 200 + 空列表。"""
    r = client.get("/api/market/realtime")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, list), f"应为 list，实际 {type(data)}"
    # 无 DB 时返回空列表（endpoint 内部 try/except 兜底）
    assert data == [], f"无 DB 时应返回 []，实际 {data[:5]}"


def test_market_summary(client: TestClient) -> None:
    """GET /api/market/summary 无 DB 时应返回 200 + 零值占位结构。"""
    r = client.get("/api/market/summary")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    assert data.get("total_stocks") == 0
    assert data.get("daily_bars") == 0


# ── 4. 新闻 ──


def test_news(client: TestClient) -> None:
    """GET /api/news 无本地 DB 时应回退 akshare 并返回 200 + 新闻列表。"""
    r = client.get("/api/news", params={"symbol": "000001", "limit": 5})
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    # 即使 news_items 表不存在，也应返回 news 列表（可能来自 akshare 回退或空）
    assert "news" in data, f"缺少 news 字段: {list(data.keys())}"
    assert isinstance(data["news"], list)
    # 确认 source 字段存在
    assert "source" in data, f"缺少 source 字段"
    # sentiment 应为一个 dict 结构（即使无数据）
    assert "sentiment" in data, f"缺少 sentiment 字段"
    if data["source"] is None:
        # 完全无新闻时的兜底结构
        assert len(data["news"]) == 0


# ── 5. 数据状态 ──


def test_data_status(client: TestClient) -> None:
    """GET /api/data/status 无 DB 时应返回 200 + ok=False 的结构化响应。"""
    r = client.get("/api/data/status")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    # 无 DB 时 ok=False，单结构完整
    assert data.get("ok") is False, f"无 DB 时 ok 应为 False，实际 {data.get('ok')}"
    assert "source" in data
    assert "stocks" in data
    assert "daily_bars" in data
    assert "breakdown" in data, f"缺少 breakdown 字段"
    assert isinstance(data["breakdown"], dict)
    # 各统计值应为 0 或 None
    assert data.get("stocks") == 0
    assert data.get("daily_bars") == 0


# ── 6. 额外的健壮性测试：K 线无 DB ──


def test_market_klines_without_db(client: TestClient) -> None:
    """GET /api/market/klines 无 DB 时应返回 200 + stub 源的 空 K 线结构。"""
    r = client.get("/api/market/klines", params={"symbol": "000001", "interval": "1d", "limit": 10})
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    # klines 端点在无任何数据源时返回空数据 + source=none/stub
    inner = data.get("data") or data
    assert isinstance(inner, dict)
    # 应有 limit/data/interval/symbol 等字段
    assert "data" in inner
    assert isinstance(inner["data"], list)


# ── 7. 非 DB 依赖端点：dashboard ──


def test_dashboard_without_db(client: TestClient) -> None:
    """GET /api/dashboard 无 DB 时应返回 200 + 零值占位。"""
    r = client.get("/api/dashboard")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    # 最少应有 total_equity 或 dashboard_notes
    assert "total_equity" in data or "dashboard_notes" in data


# ── 8. 策略列表（静态返回，不依赖 DB） ──


def test_strategies_without_db(client: TestClient) -> None:
    """GET /api/strategies 应返回 200 + strategies 列表。"""
    r = client.get("/api/strategies")
    assert r.status_code == 200, f"期望 200，实际 {r.status_code}: {r.text[:200]}"
    data = r.json()
    assert isinstance(data, dict)
    assert "strategies" in data
    assert isinstance(data["strategies"], list)
    # 策略列表是硬编码/从文件加载的，不依赖 DB，应有至少 1 个
    assert len(data["strategies"]) >= 1, f"策略列表为空"


# ── 9. 验证根路径 ──


def test_root_redirect(client: TestClient) -> None:
    """GET / 应 302 跳转到 /docs。"""
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 302, f"期望 302 重定向，实际 {r.status_code}"
    assert "/docs" in r.headers.get("location", ""), f"应指向 /docs"
