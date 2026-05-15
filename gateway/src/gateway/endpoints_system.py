"""System API endpoints."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# --- shared helpers imported from endpoints.py ---

from .endpoints_helpers import (  # noqa: E402
    _pipeline_quant_data_status,
    _status_to_state,
)


# --- System Routes ---


@router.get("/data/status")
def get_data_status() -> dict:
    """数据状态：合并 astock 表与 pipeline 表口径，供「数据」页与 Dashboard；主数字优先与概览一致。"""
    astock_st: Optional[dict] = None
    try:
        from data_engine import get_astock_duckdb_available, get_duckdb_data_status

        if get_astock_duckdb_available():
            astock_st = get_duckdb_data_status()
    except Exception:
        _log.error("Import failed", exc_info=True)

    pipeline_st = _pipeline_quant_data_status()

    def _has_data(d: Optional[dict]) -> bool:
        if not d:
            return False
        return (d.get("daily_bars") or 0) > 0 or (d.get("stocks") or 0) > 0

    primary: Optional[dict] = None
    source_label: Optional[str] = None
    if _has_data(pipeline_st):
        primary = pipeline_st
        source_label = "duckdb_pipeline"
    elif _has_data(astock_st):
        primary = astock_st
        source_label = "duckdb_astock"
    elif pipeline_st:
        primary = pipeline_st
        source_label = "duckdb_pipeline"
    elif astock_st:
        primary = astock_st
        source_label = "duckdb_astock"

    if primary:
        return {
            "ok": True,
            "source": source_label,
            **primary,
            "breakdown": {
                "astock_schema": astock_st,
                "pipeline_schema": pipeline_st,
            },
        }

    return {
        "ok": False,
        "source": None,
        "stocks": 0,
        "daily_bars": 0,
        "date_min": None,
        "date_max": None,
        "breakdown": {"astock_schema": astock_st, "pipeline_schema": pipeline_st},
    }


@router.get("/data/daily-coverage")
def get_daily_coverage(limit_codes: int = 200) -> dict:
    """
    a_stock_daily 覆盖明细：总行数、有 K 线的标的数、每只有多少根 K 线 TopN。
    用于解释「股票池很大但日线总行数很少」——多为仅部分标的/短区间写入。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"ok": False, "error": "database_not_found", "top_codes": []}
        conn = get_conn(read_only=True)
        try:
            lim = max(10, min(int(limit_codes or 200), 500))
            agg = conn.execute(
                """
                SELECT COUNT(*), COUNT(DISTINCT code), MIN(date), MAX(date)
                FROM a_stock_daily
                """
            ).fetchone()
            total_rows = int(agg[0] or 0) if agg else 0
            distinct_codes = int(agg[1] or 0) if agg else 0
            date_min = str(agg[2])[:10] if agg and agg[2] is not None else None
            date_max = str(agg[3])[:10] if agg and agg[3] is not None else None
            pool_row = conn.execute("SELECT COUNT(*) FROM a_stock_basic").fetchone()
            stock_pool = int(pool_row[0] or 0) if pool_row else 0
            top_rows = conn.execute(
                """
                SELECT code, COUNT(*) AS n, MIN(date), MAX(date)
                FROM a_stock_daily
                GROUP BY code
                ORDER BY n DESC
                LIMIT ?
                """,
                [lim],
            ).fetchall()
            top_codes = [
                {
                    "code": str(r[0]),
                    "bar_count": int(r[1] or 0),
                    "date_min": str(r[2])[:10] if r[2] is not None else None,
                    "date_max": str(r[3])[:10] if r[3] is not None else None,
                }
                for r in top_rows
            ]
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
        avg = (total_rows / distinct_codes) if distinct_codes else 0.0
        return {
            "ok": True,
            "total_rows": total_rows,
            "distinct_codes": distinct_codes,
            "stock_pool_codes": stock_pool,
            "avg_bars_per_code": round(avg, 4),
            "date_min": date_min,
            "date_max": date_max,
            "top_codes": top_codes,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "top_codes": []}


@router.get("/data/sources")
def get_data_sources() -> dict:
    """已注册数据源 id 列表（支持增量更新的数据源）。"""
    try:
        from data_pipeline import list_sources

        return {"sources": list_sources()}
    except Exception as e:
        return {"sources": [], "error": str(e)}


@router.post("/data/ensure-stocks")
def ensure_stocks() -> dict:
    """拉取 A 股股票池写入 a_stock_basic（akshare），数据不足时由前端或定时任务调用。"""
    try:
        from data_pipeline.collectors.stock_list import update_stock_list

        n = update_stock_list()
        return {"ok": True, "rows": n}
    except Exception as e:
        return {"ok": False, "rows": 0, "error": str(e)}


@router.post("/data/incremental")
def run_data_incremental(
    source_id: str = Query(
        "ashare_daily_kline",
        description="数据源 ID：ashare_daily_kline（东财/akshare）或 tushare_daily（需 TUSHARE_TOKEN）；见 GET /api/data/sources",
    ),
    force_full: bool = Query(False, description="为 True 时对 ashare_daily_kline 全员重拉约一年"),
    codes_limit: Optional[int] = Query(
        None,
        ge=1,
        le=8000,
        description="仅 ashare_daily_kline：最多处理 a_stock_basic 前 N 只，分批防超时；不传则最多 8000",
    ),
    verbose: bool = Query(
        False,
        description="为 True 时 ashare_daily_kline 将分批进度打到服务 stderr",
    ),
    no_proxy: bool = Query(
        False,
        description="为 True 时 ashare_daily_kline 临时清除环境变量中所有 *proxy* 项再请求（修坏代理）",
    ),
) -> dict:
    """执行指定数据源增量更新。ashare_daily_kline 已从 a_stock_basic 扩量，并区分「无 K 线」回填与增量。"""
    try:
        from data_pipeline import run_incremental, list_sources

        if source_id not in list_sources():
            raise HTTPException(status_code=400, detail=f"unknown source_id: {source_id}")
        kw = {}
        if codes_limit is not None:
            kw["codes_limit"] = codes_limit
        if verbose and source_id in ("ashare_daily_kline", "tushare_daily"):
            kw["verbose"] = True
        if no_proxy and source_id in ("ashare_daily_kline", "tushare_daily"):
            kw["strip_proxy_env"] = True
        n = run_incremental(source_id, force_full=force_full, **kw)
        return {"ok": True, "source_id": source_id, "rows_written": n, "codes_limit": codes_limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/system/status")
def get_system_status(limit: int = 10):
    """
    统一运行核心状态（system_status 表），由 system_core 写入。
    返回：summary（data_pipeline, scanner, ai_models, strategy_engine, last_update）+ history 列表。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {
                "data_pipeline": "idle",
                "scanner": "idle",
                "ai_models": "idle",
                "strategy_engine": "idle",
                "last_update": None,
                "history": [],
            }
        conn = get_conn(read_only=False)
        try:
            df = conn.execute(
                """SELECT data_status, scanner_status, ai_status, strategy_status, snapshot_time,
                          evolution_task_id, evolution_status, evolution_result, skill_call_count, skill_last_call_time
                   FROM system_status ORDER BY snapshot_time DESC LIMIT ?""",
                [limit],
            ).fetchdf()
        except Exception:
            df = conn.execute(
                "SELECT data_status, scanner_status, ai_status, strategy_status, snapshot_time FROM system_status ORDER BY snapshot_time DESC LIMIT ?",
                [limit],
            ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {
                "data_pipeline": "idle",
                "scanner": "idle",
                "ai_models": "idle",
                "strategy_engine": "idle",
                "last_update": None,
                "history": [],
                "evolution_task_id": None,
                "evolution_status": None,
                "skill_call_count": 0,
                "skill_last_call_time": None,
            }
        row = df.iloc[0]
        last_ts = row.get("snapshot_time")
        if hasattr(last_ts, "isoformat"):
            last_update = last_ts.isoformat()
        else:
            last_update = str(last_ts) if last_ts else None
        summary = {
            "data_pipeline": _status_to_state(str(row.get("data_status", ""))),
            "scanner": _status_to_state(str(row.get("scanner_status", ""))),
            "ai_models": _status_to_state(str(row.get("ai_status", ""))),
            "strategy_engine": _status_to_state(str(row.get("strategy_status", ""))),
            "last_update": last_update,
        }
        if "evolution_task_id" in row:
            summary["evolution_task_id"] = row.get("evolution_task_id")
            summary["evolution_status"] = row.get("evolution_status")
        if "skill_call_count" in row:
            summary["skill_call_count"] = int(row.get("skill_call_count") or 0)
            st = row.get("skill_last_call_time")
            summary["skill_last_call_time"] = (
                st.isoformat() if hasattr(st, "isoformat") else (str(st) if st else None)
            )
        history = df.to_dict(orient="records")
        for h in history:
            if "snapshot_time" in h and hasattr(h["snapshot_time"], "isoformat"):
                h["snapshot_time"] = h["snapshot_time"].isoformat()
        return {**summary, "history": history}
    except Exception:
        return {
            "data_pipeline": "idle",
            "scanner": "idle",
            "ai_models": "idle",
            "strategy_engine": "idle",
            "last_update": None,
            "history": [],
            "evolution_task_id": None,
            "evolution_status": None,
            "skill_call_count": 0,
            "skill_last_call_time": None,
        }


@router.get("/system/health-detail")
def get_system_health_detail() -> dict:
    """健康检查扩展：Celery worker 探测、pipeline_meta 最近项、Prometheus 路径（供运维 / OpenClaw）。"""
    try:
        from .endpoints_health import build_health_detail_payload

        return json_ok(build_health_detail_payload(), source="gateway")
    except Exception as e:
        return json_fail(str(e)[:200], status_code=503)


@router.get("/health/detailed")
def get_health_detailed_alias() -> dict:
    """与 /system/health-detail 等价，便于监控与小程序统一路径。"""
    try:
        from .endpoints_health import build_health_detail_payload

        return json_ok(build_health_detail_payload(), source="health")
    except Exception as e:
        return json_fail(str(e)[:200], status_code=503)


@router.get("/system/backtest-errors")
def get_system_backtest_errors(limit: int = 20) -> dict:
    """Celery / 回测任务最近错误（backtest_task_errors），供排障。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables, get_db_path

        lim = max(1, min(limit, 200))
        if not os.path.isfile(get_db_path()):
            return json_ok({"items": []}, source="none")
        conn = get_conn(read_only=False)
        ensure_tables(conn)
        try:
            df = conn.execute(
                """
                SELECT id, task_name, strategy_id,
                       SUBSTRING(payload_json, 1, 400) AS payload_preview,
                       SUBSTRING(error_message, 1, 500) AS error_message,
                       created_at
                FROM backtest_task_errors
                ORDER BY id DESC LIMIT ?
                """,
                [lim],
            ).fetchdf()
        except Exception:
            df = None
        conn.close()
        if df is None or df.empty:
            return json_ok({"items": []}, source="duckdb")
        return json_ok({"items": df.to_dict(orient="records")}, source="duckdb")
    except Exception as e:
        return json_fail(str(e)[:200], status_code=503)


@router.get("/data/quality")
def get_data_quality() -> Any:
    """最近一条数据质量巡检报告（DuckDB data_quality_reports）。"""
    try:
        from .endpoints_health import _ensure_repo_paths_for_health

        _ensure_repo_paths_for_health()
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

        path = get_db_path()
        if not path or not os.path.isfile(path):
            return json_ok(None, source="none")
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
            row = conn.execute(
                """
                SELECT id, report_json, run_at
                FROM data_quality_reports
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        finally:
            try:
                conn.close()
            except Exception:
                _log.error("Failed to close database connection", exc_info=True)
        if not row:
            return json_ok(None, source="duckdb")
        raw = row[1]
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            parsed = {"raw": raw}
        return json_ok(
            {"id": row[0], "run_at": str(row[2]) if row[2] is not None else None, "report": parsed},
            source="duckdb",
        )
    except Exception as e:
        _log.exception("get_data_quality failed")
        return json_ok(None, source="unavailable")


@router.get("/audit/logs")
def get_audit_logs(limit: int = 100) -> dict:
    """审计日志：最近请求记录。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"logs": []}
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT id, method, path, client_host, created_at FROM audit_log ORDER BY id DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {"logs": []}
        return {"logs": df.to_dict("records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
