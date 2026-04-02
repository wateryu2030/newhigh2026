"""
Prometheus 指标：data_pipeline_latency、scan_latency、ai_latency、trade_latency 等。
供 /metrics 暴露，Grafana 可据此绘图。
"""

from __future__ import annotations

_latency = None
_request_count = None


def _get_latency_histogram():
    global _latency
    if _latency is not None:
        return _latency
    try:
        from prometheus_client import Histogram

        _latency = Histogram(
            "pipeline_stage_latency_seconds",
            "Request latency by pipeline stage (data/scan/ai/trade)",
            ["stage"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
        )
        return _latency
    except ImportError:
        return None


def _get_request_count():
    global _request_count
    if _request_count is not None:
        return _request_count
    try:
        from prometheus_client import Counter

        _request_count = Counter(
            "gateway_requests_total",
            "Total API requests by stage",
            ["stage", "method"],
        )
        return _request_count
    except ImportError:
        return None


def path_to_stage(path: str) -> str:
    """将请求路径映射为 pipeline stage 标签。"""
    p = (path or "").strip()
    if "/api/data/" in p:
        return "data"
    if "/api/market/" in p or "/api/strategy/signals" in p:
        return "scan"
    if "/api/ai/" in p:
        return "ai"
    if "/api/simulated/" in p or "/api/execution/" in p or "/api/trades" in p:
        return "trade"
    if "/api/backtest/" in p:
        return "backtest"
    if "/api/system/health" in p or "/api/system/backtest-errors" in p:
        return "ops"
    return "other"


def record_request(latency_seconds: float, path: str, method: str = "GET") -> None:
    """记录一次请求的耗时与 stage。"""
    stage = path_to_stage(path)
    h = _get_latency_histogram()
    if h is not None:
        try:
            h.labels(stage=stage).observe(latency_seconds)
        except Exception:
            pass
    c = _get_request_count()
    if c is not None:
        try:
            c.labels(stage=stage, method=method.upper()).inc()
        except Exception:
            pass
