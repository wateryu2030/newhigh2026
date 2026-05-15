"""Frontend API endpoints."""

from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# --- shared helpers imported from endpoints.py ---

from .endpoints import (  # noqa: E402
    _status_to_state,
    _metrics_from_equity_curve,
    _dashboard_top_strategies_from_db,
    _dashboard_from_duckdb,
    _alpha_lab_binding_note,
    _alpha_lab_compute_counts,
    _alpha_lab_drill_rows,
    _alpha_lab_code6,
    _run_evolution_background,
)


# --- Frontend Routes ---


@router.get("/ai/decision")
def get_ai_decision() -> dict:
    """
    AI 决策解释：聚合情绪、交易信号、游资、主线，返回当前信号与理由，供前端「AI 决策解释」区块展示。
    返回：signal (BUY/SELL/HOLD), reason (文案), factors (标签列表)。
    """
    signal = "HOLD"
    reason_parts: List[str] = []
    factors: List[str] = []
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"signal": signal, "reason": "暂无数据", "factors": []}
        conn = get_conn(read_only=False)
        try:
            row = conn.execute(
                "SELECT emotion_state, limitup_count FROM market_emotion ORDER BY trade_date DESC LIMIT 1"
            ).fetchone()
            if row:
                stage = str(row[0] or "—")
                limitup = int(row[1] or 0)
                reason_parts.append(f"情绪阶段: {stage}; 涨停数 {limitup}")
                factors.append(f"emotion_{stage[:2]}" if stage != "—" else "emotion")
            df_sig = conn.execute(
                "SELECT signal FROM trade_signals ORDER BY snapshot_time DESC LIMIT 20"
            ).fetchdf()
            if df_sig is not None and not df_sig.empty:
                sig_str = str(df_sig.iloc[0].get("signal", "")).upper()
                if "BUY" in sig_str or "LONG" in sig_str or "买" in sig_str or "多" in sig_str:
                    signal = "BUY"
                elif "SELL" in sig_str or "SHORT" in sig_str or "卖" in sig_str or "空" in sig_str:
                    signal = "SELL"
                n = len(df_sig)
                reason_parts.append(f"交易信号 {n} 条，最新: {sig_str or '—'}")
                factors.append("trade_signals")
            hot = conn.execute("SELECT COUNT(*) FROM top_hotmoney_seats").fetchone()
            hot_n = int(hot[0]) if hot and hot[0] is not None else 0
            if hot_n > 0:
                reason_parts.append(f"游资席位 {hot_n} 个")
                factors.append("hotmoney")
            th = conn.execute("SELECT COUNT(*) FROM main_themes").fetchone()
            th_n = int(th[0]) if th and th[0] is not None else 0
            if th_n > 0:
                reason_parts.append(f"主线题材 {th_n} 个")
                factors.append("themes")
        finally:
            conn.close()
        reason = (
            "；".join(reason_parts)
            if reason_parts
            else "暂无情绪与信号数据，建议先运行 system_core。"
        )
    except Exception as e:
        reason = str(e)
    return {"signal": signal, "reason": reason, "factors": factors}


@router.post("/ai/generate-strategies")
def generate_strategies(count: int = 5) -> dict:
    """Generate strategies via AI (stub)."""
    return {"generated": [], "count": count}


@router.get("/dashboard")
def get_dashboard() -> dict:
    """Dashboard：有 DuckDB 时用日线推导权益曲线与日涨跌；夏普/回撤由曲线估算；策略榜仅 DB 真实记录。"""
    try:
        out = _dashboard_from_duckdb()
        if out is not None:
            return out
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    stub_equity = [10e6, 10.2e6, 10.5e6, 11e6, 11.8e6, 12.34e6]
    sh, md = _metrics_from_equity_curve(stub_equity)
    return {
        "total_equity": 12_340_000,
        "daily_return_pct": 2.34,
        "sharpe_ratio": sh if sh is not None else None,
        "max_drawdown_pct": md if md is not None else None,
        "equity_curve": stub_equity,
        "top_strategies": [],
        "ai_generated_today": None,
        "strategies_alive": None,
        "strategies_live": None,
        "equity_proxy_symbol": None,
        "dashboard_notes": ["no_duckdb_or_no_bars_using_static_demo_equity_curve"],
    }


@router.get("/evolution")
def get_evolution() -> dict:
    """Evolution：优先从 DuckDB evolution_tasks 最近一条 success 结果摘要；否则返回演示数据。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=True)
            row = conn.execute(
                """
                SELECT result FROM evolution_tasks
                WHERE lower(status) = 'success' AND result IS NOT NULL AND length(trim(result)) > 2
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
            conn.close()
            if row and row[0]:
                try:
                    res = json.loads(row[0])
                except Exception:
                    res = None
                if isinstance(res, dict) and not res.get("error"):
                    gen = int(res.get("generation") or 1)
                    staged = res.get("staged") if isinstance(res.get("staged"), list) else []
                    best_strategy = None
                    if staged:
                        def _sharpe_key(c: dict) -> float:
                            try:
                                return float(c.get("sharpe_ratio") or -1e9)
                            except (TypeError, ValueError):
                                return -1e9

                        dict_rows = [x for x in staged if isinstance(x, dict)]
                        if dict_rows:
                            b = max(dict_rows, key=_sharpe_key)
                            sid = str(b.get("strategy_id") or "unknown")
                            try:
                                sh = float(b.get("sharpe_ratio") or 0)
                            except (TypeError, ValueError):
                                sh = 0.0
                            try:
                                rp = float(b.get("return_pct") or 0)
                            except (TypeError, ValueError):
                                rp = 0.0
                            best_strategy = {"id": sid, "sharpe": sh, "return_pct": rp}
                    return {
                        "current_generation": gen,
                        "best_strategy": best_strategy,
                        "generations": [{"gen": gen}],
                        "source": "duckdb",
                    }
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    return {
        "current_generation": 3,
        "best_strategy": {"id": "STR_0034", "sharpe": 2.6, "return_pct": 41},
        "generations": [{"gen": 1}, {"gen": 2}, {"gen": 3}],
        "source": "demo",
    }


@router.post("/evolution/run")
def post_evolution_run(
    population_limit: int = 10,
    symbol: str = "000001.SZ",
) -> dict:
    """执行一轮 OpenClaw 进化：从策略市场加载种群，遗传+回测评估，优秀个体写回 strategy_market。"""
    try:
        import os as _os
        import sys as _sys

        _root = _os.path.dirname(
            _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        )
        for _d in ["openclaw_engine", "backtest-engine/src", "data-pipeline/src", "core/src"]:
            _p = _os.path.join(_root, _d)
            if _os.path.isdir(_p) and _p not in _sys.path:
                _sys.path.insert(0, _p)
        from openclaw_engine import run_evolution_cycle

        return run_evolution_cycle(population_limit=population_limit, symbol=symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evolution/trigger")
def post_evolution_trigger(
    task_type: str = "strategy_generation",
    population_limit: int = 10,
    symbol: str = "000001.SZ",
) -> dict:
    """触发 OpenClaw 进化任务（异步），返回 task_id；前端可轮询 GET /api/evolution/status/{task_id}。"""
    task_id = str(uuid.uuid4())
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            conn.execute(
                "INSERT INTO evolution_tasks (task_id, status, result) VALUES (?, ?, ?)",
                [task_id, "pending", None],
            )
            conn.close()
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    t = threading.Thread(
        target=_run_evolution_background,
        args=(task_id, population_limit, symbol),
        daemon=True,
    )
    t.start()
    return {"task_id": task_id, "status": "pending"}


@router.get("/evolution/status/{task_id}")
def get_evolution_status(task_id: str) -> dict:
    """查询 OpenClaw 进化任务状态与结果。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"task_id": task_id, "status": "PENDING", "result": None}
        conn = get_conn(read_only=False)
        row = conn.execute(
            "SELECT status, result FROM evolution_tasks WHERE task_id = ?",
            [task_id],
        ).fetchone()
        conn.close()
        if not row:
            return {"task_id": task_id, "status": "PENDING", "result": None}
        status, res_str = row[0], row[1]
        result = None
        if res_str:
            try:
                result = json.loads(res_str)
            except Exception:
                result = res_str
        return {"task_id": task_id, "status": status.upper(), "result": result}
    except Exception:
        return {"task_id": task_id, "status": "PENDING", "result": None}


@router.get("/evolution/tasks")
def get_evolution_tasks(limit: int = 5) -> dict:
    """最近若干次进化任务列表，供系统监控页展示。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"tasks": []}
        conn = get_conn(read_only=False)
        df = conn.execute(
            "SELECT task_id, status, result, created_at FROM evolution_tasks ORDER BY created_at DESC LIMIT ?",
            [limit],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return {"tasks": []}
        tasks = []
        for _, row in df.iterrows():
            tasks.append(
                {
                    "id": str(row.get("task_id", "")),
                    "status": str(row.get("status", "pending")),
                    "result": row.get("result"),
                    "created_at": (
                        row.get("created_at").isoformat()
                        if hasattr(row.get("created_at"), "isoformat")
                        else str(row.get("created_at")) if row.get("created_at") else None
                    ),
                }
            )
        return {"tasks": tasks}
    except Exception:
        return {"tasks": []}


@router.get("/trades")
def get_trades(limit: int = 50) -> dict:
    """Recent trades (stub)."""
    return {
        "trades": [
            {
                "time": "2025-03-07T10:00:00Z",
                "strategy": "STR_001",
                "symbol": "BTCUSDT",
                "side": "BUY",
                "qty": 0.1,
                "price": 95000,
            },
            {
                "time": "2025-03-07T09:30:00Z",
                "strategy": "STR_002",
                "symbol": "ETHUSDT",
                "side": "SELL",
                "qty": 1.0,
                "price": 3500,
            },
        ][:limit],
    }


@router.get("/alpha-lab/drill")
def get_alpha_lab_drill(stage: str = "generated", limit: int = 100) -> dict:
    """Alpha 工坊下钻：按阶段返回标的列表（与 /alpha-lab 同一 DuckDB 口径）。"""
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

        note = _alpha_lab_binding_note()
        if not os.path.isfile(get_db_path()):
            return {"stage": stage, "items": [], "total": 0, "source": "stub_no_db", "binding_note": note}
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
            items = _alpha_lab_drill_rows(conn, stage, limit)
            return {
                "stage": stage,
                "items": items,
                "total": len(items),
                "source": "duckdb",
                "binding_note": note,
            }
        finally:
            conn.close()
    except Exception:
        _log.exception("get_alpha_lab_drill")
        return {
            "stage": stage,
            "items": [],
            "total": 0,
            "source": "error",
            "binding_note": _alpha_lab_binding_note(),
        }


@router.get("/alpha-lab")
def get_alpha_lab() -> dict:
    """Alpha 工坊漏斗：优先 DuckDB 代理指标；无库或失败时返回 0。"""
    note = _alpha_lab_binding_note()
    try:
        from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {
                "generated_today": 0,
                "passed_backtest": 0,
                "passed_risk": 0,
                "deployed": 0,
                "source": "stub_no_db",
                "binding_note": note,
            }
        conn = get_conn(read_only=False)
        try:
            ensure_tables(conn)
            out = _alpha_lab_compute_counts(conn)
            out["source"] = "duckdb"
            out["binding_note"] = note
            return out
        finally:
            conn.close()
    except Exception:
        _log.exception("get_alpha_lab")
        return {
            "generated_today": 0,
            "passed_backtest": 0,
            "passed_risk": 0,
            "deployed": 0,
            "source": "error",
            "binding_note": note,
        }
