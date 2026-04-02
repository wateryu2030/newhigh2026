"""
统一健康检查：依赖连通性、关键表数据量与阈值（degraded）。
供 GET /api/health 与根路径 /health 复用。
"""

from __future__ import annotations

import logging
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


def _ensure_repo_paths_for_health() -> None:
    """保证可 import data_pipeline、system_core（健康详情需 Celery inspect）。"""
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    for sub in ("data-pipeline/src", "core/src", "execution-engine/src"):
        p = root / sub
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))

# 可经环境变量覆盖
_TOP10_MIN_ROWS = int(os.environ.get("HEALTH_TOP10_MIN_ROWS", "1000"))
_BASIC_MIN_ROWS = int(os.environ.get("HEALTH_BASIC_MIN_ROWS", "100"))


def _safe_count(conn, sql: str) -> tuple[int | None, str | None]:
    try:
        row = conn.execute(sql).fetchone()
        if row is None:
            return None, None
        return int(row[0]), None
    except Exception as e:
        return None, str(e)[:200]


def build_health_payload() -> Dict[str, Any]:
    """返回 status、services、data_availability、checks（兼容旧字段）。"""
    _ensure_repo_paths_for_health()
    status = "ok"
    services: Dict[str, Any] = {}
    data_availability: Dict[str, Any] = {}
    checks: Dict[str, Any] = {}

    # --- DuckDB（data_pipeline 统一路径）---
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables, get_db_path

        db_path = get_db_path()
        if not os.path.isfile(db_path):
            services["duckdb"] = {"status": "error", "error": "database file not found", "path": db_path}
            checks["db"] = "unavailable"
            status = "degraded"
        else:
            # 与 Gateway 内其他 DuckDB 访问一致须 read_only=False，否则与审计写入混用会报错：
            # "Can't open a connection ... different configuration"
            conn = get_conn(read_only=False)
            try:
                ensure_tables(conn)
                conn.execute("SELECT 1").fetchone()
                services["duckdb"] = {"status": "ok", "path": db_path}

                n_basic, err_b = _safe_count(conn, "SELECT COUNT(*) FROM a_stock_basic")
                if err_b:
                    data_availability["a_stock_basic"] = {"error": err_b}
                else:
                    data_availability["a_stock_basic"] = {"row_count": n_basic}
                    if n_basic is not None and n_basic < _BASIC_MIN_ROWS:
                        status = "degraded"

                n_top10, err_t = _safe_count(conn, "SELECT COUNT(*) FROM top_10_shareholders")
                if err_t:
                    data_availability["top_10_shareholders"] = {"error": err_t}
                else:
                    data_availability["top_10_shareholders"] = {"row_count": n_top10}
                    if n_top10 is not None and n_top10 < _TOP10_MIN_ROWS:
                        status = "degraded"

                n_daily, err_d = _safe_count(conn, "SELECT COUNT(*) FROM a_stock_daily")
                if err_d:
                    data_availability["a_stock_daily"] = {"error": err_d}
                else:
                    last_d: str | None = None
                    try:
                        r2 = conn.execute("SELECT MAX(date) FROM a_stock_daily").fetchone()
                        last_d = str(r2[0]) if r2 and r2[0] is not None else None
                    except Exception:
                        pass
                    # 文档中的 market_ohlcv 在本仓库对应 a_stock_daily 日线表
                    data_availability["a_stock_daily"] = {
                        "row_count": n_daily,
                        "last_date": last_d,
                        "alias": "market_ohlcv_daily",
                    }

                checks["db"] = "available"
            except Exception as e:
                logger.exception("DuckDB health check failed")
                services["duckdb"] = {"status": "error", "error": str(e)[:200]}
                checks["db"] = "error"
                checks["db_error"] = str(e)[:200]
                status = "degraded"
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    except Exception as e:
        logger.exception("DuckDB import or path failed")
        services["duckdb"] = {"status": "error", "error": str(e)[:200]}
        checks["db"] = "error"
        status = "degraded"

    # --- ClickHouse（可选）---
    ch_url = os.environ.get("CLICKHOUSE_URL", "").strip()
    if ch_url.startswith("http://") or ch_url.startswith("https://"):
        try:
            import urllib.request

            q = ch_url.rstrip("/") + "/?query=" + urllib.parse.quote("SELECT 1", safe="")
            req = urllib.request.Request(q, method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                _ = resp.read(16)
            services["clickhouse"] = {"status": "ok"}
        except Exception as e:
            services["clickhouse"] = {"status": "error", "error": str(e)[:120]}
            status = "degraded"
    elif ch_url:
        services["clickhouse"] = {"status": "skipped", "reason": "CLICKHOUSE_URL 非 HTTP 接口，跳过探测"}
    else:
        services["clickhouse"] = {"status": "skipped", "reason": "CLICKHOUSE_URL not set"}

    return {
        "status": status,
        "services": services,
        "data_availability": data_availability,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _celery_inspect_brief() -> Dict[str, Any]:
    broker = os.environ.get("CELERY_BROKER_URL", "").strip()
    if not broker:
        return {"status": "skipped", "reason": "CELERY_BROKER_URL not set"}
    try:
        from system_core.celery_app import app as celery_app

        if celery_app is None:
            return {"status": "skipped", "reason": "celery not installed or import failed"}
        insp = celery_app.control.inspect(timeout=1.0)
        if insp is None:
            return {"status": "degraded", "reason": "inspect unavailable"}
        ping = insp.ping()
        if ping:
            return {"status": "ok", "workers": list(ping.keys())}
        return {"status": "degraded", "reason": "no worker ping response"}
    except TypeError:
        try:
            from system_core.celery_app import app as celery_app

            if celery_app is None:
                return {"status": "skipped", "reason": "celery_app_none"}
            insp = celery_app.control.inspect()
            if insp is None:
                return {"status": "degraded", "reason": "inspect unavailable"}
            ping = insp.ping()
            if ping:
                return {"status": "ok", "workers": list(ping.keys())}
            return {"status": "degraded", "reason": "no worker ping response"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}
    except Exception as e:
        return {"status": "error", "error": str(e)[:200]}


def _pipeline_meta_recent() -> list:
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables, get_db_path

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        ensure_tables(conn)
        df = conn.execute(
            "SELECT k, v, updated_at FROM pipeline_meta ORDER BY updated_at DESC LIMIT 8"
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        return df.to_dict(orient="records")
    except Exception:
        return []


def build_health_detail_payload() -> Dict[str, Any]:
    """在 build_health_payload 基础上增加 Celery、pipeline_meta、Prometheus 路径提示。"""
    out = build_health_payload()
    out["celery"] = _celery_inspect_brief()
    out["pipeline_meta_recent"] = _pipeline_meta_recent()
    out["prometheus_metrics_path"] = "/metrics"
    _webhook = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    out["alert_webhook_configured"] = bool(_webhook)
    return out
