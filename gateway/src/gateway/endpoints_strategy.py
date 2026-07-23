"""Strategy API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from .response_utils import json_fail, json_ok

router = APIRouter()
_log = logging.getLogger(__name__)

# --- shared helpers imported from endpoints.py ---

from .endpoints_helpers import (  # noqa: E402
    _short_ts_for_signal,
    _optional_price,
    _optional_pct,
    _save_backtest_to_strategy_market,
    _run_backtest_internal,
    _risk_engine_module,
)


# --- Strategy Routes ---


@router.get("/strategy/signals")
def get_strategy_signals(limit: int = 50) -> list:
    """
    交易信号：联接股票名称、现价/涨跌幅（实时或最近日线），时间缩略到分。
    返回字段供传统行情表展示，不含原始微秒级 snapshot_time。
    """
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return []
        conn = get_conn(read_only=False)
        lim = max(1, min(int(limit or 50), 500))
        df = conn.execute(
            """
            SELECT
                t.code,
                COALESCE(b.name, '') AS stock_name,
                t.signal,
                t.confidence,
                t.target_price,
                t.stop_loss,
                t.strategy_id,
                t.signal_score,
                COALESCE(rt.latest_price, ld.c) AS last_price,
                rt.change_pct AS change_pct,
                t.snapshot_time
            FROM trade_signals t
            LEFT JOIN a_stock_basic b ON b.code = t.code
            LEFT JOIN a_stock_realtime rt ON rt.code = t.code
            LEFT JOIN (
                SELECT code, close AS c,
                    ROW_NUMBER() OVER (PARTITION BY code ORDER BY date DESC) AS rn
                FROM a_stock_daily
            ) ld ON ld.code = t.code AND ld.rn = 1
            ORDER BY t.snapshot_time DESC
            LIMIT ?
            """,
            [lim],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            out.append(
                {
                    "code": str(row.get("code") or ""),
                    "stock_name": str(row.get("stock_name") or "").strip(),
                    "signal": str(row.get("signal") or ""),
                    "confidence": float(row["confidence"])
                    if row.get("confidence") is not None
                    else None,
                    "signal_score": float(row["signal_score"])
                    if row.get("signal_score") is not None
                    else None,
                    "target_price": _optional_price(row.get("target_price")),
                    "stop_loss": _optional_price(row.get("stop_loss")),
                    "strategy_id": str(row.get("strategy_id") or ""),
                    "last_price": _optional_price(row.get("last_price")),
                    "change_pct": _optional_pct(row.get("change_pct")),
                    "updated_at": _short_ts_for_signal(row.get("snapshot_time")),
                }
            )
        return out
    except Exception:
        return []


@router.get("/strategies")
def list_strategies() -> dict:
    """List strategy types (stub)."""
    return {
        "strategies": [
            {"id": "trend_following", "name": "Trend Following"},
            {"id": "mean_reversion", "name": "Mean Reversion"},
            {"id": "breakout", "name": "Breakout"},
        ]
    }


@router.get("/strategies/market")
def get_strategies_market(limit: int = 50) -> dict:
    """
    策略市场列表：id、名称、收益、Sharpe、回撤、状态。
    优先从 strategy_market 表读（回测结果写入）；再补 trade_signals 中 distinct strategy_id。
    无数据时返回空列表，不注入演示用假收益。
    """
    items: List[dict] = []
    seen: set = set()
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if os.path.isfile(get_db_path()):
            conn = get_conn(read_only=False)
            try:
                df = conn.execute(
                    """SELECT strategy_id, name, return_pct, sharpe_ratio, max_drawdown, status
                       FROM strategy_market ORDER BY updated_at DESC LIMIT ?""",
                    [limit],
                ).fetchdf()
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        sid = str(row.get("strategy_id") or "")
                        if not sid:
                            continue
                        seen.add(sid)
                        items.append(
                            {
                                "id": sid,
                                "name": str(row.get("name") or sid.replace("_", " ").title()),
                                "return_pct": (
                                    float(row["return_pct"])
                                    if row.get("return_pct") is not None
                                    else None
                                ),
                                "sharpe_ratio": (
                                    float(row["sharpe_ratio"])
                                    if row.get("sharpe_ratio") is not None
                                    else None
                                ),
                                "max_drawdown": (
                                    float(row["max_drawdown"])
                                    if row.get("max_drawdown") is not None
                                    else None
                                ),
                                "status": str(row.get("status") or "active"),
                            }
                        )
                df2 = conn.execute(
                    """SELECT DISTINCT COALESCE(strategy_id, 'ai_fusion') AS strategy_id
                       FROM trade_signals ORDER BY strategy_id LIMIT ?""",
                    [limit],
                ).fetchdf()
                if df2 is not None and not df2.empty:
                    for sid in df2["strategy_id"].astype(str).tolist():
                        if not sid or sid == "None":
                            sid = "ai_fusion"
                        if sid in seen:
                            continue
                        seen.add(sid)
                        items.append(
                            {
                                "id": sid,
                                "name": sid.replace("_", " ").title(),
                                "return_pct": None,
                                "sharpe_ratio": None,
                                "max_drawdown": None,
                                "status": "active",
                            }
                        )
            finally:
                conn.close()
    except Exception:
        _log.error("Failed to close database connection", exc_info=True)
    return {"items": items}


@router.post("/backtest/run")
def run_backtest_api(
    request: Request,
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    signal_source: str = "trade_signals",
    init_cash: float = 10000.0,
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
    strategy_id: Optional[str] = None,
    strategy_name: Optional[str] = None,
) -> dict:
    """
    回测：从 quant_system.duckdb 读日 K 与信号，返回资金曲线与风险指标。
    若提供 strategy_id（及可选 strategy_name），回测成功后写入 strategy_market 表，供策略市场页展示。
    """
    try:
        from .auth.jwt_auth import verify_token
        from .quota_limits import check_and_increment

        auth = request.headers.get("Authorization") or ""
        ulev: str | None = None
        if auth.startswith("Bearer "):
            pl = verify_token(auth[7:].strip())
            if pl:
                ukey = str(pl.get("sub") or "").strip() or "anonymous"
                raw_lv = pl.get("user_level")
                ulev = (
                    str(raw_lv).strip()
                    if raw_lv is not None and str(raw_lv).strip()
                    else "trial"
                )
            else:
                ukey = request.client.host if request.client else "anonymous"
        else:
            ukey = request.client.host if request.client else "anonymous"
        ok_b, msg_b, _, _ = check_and_increment(ukey, "backtest", ulev)
        if not ok_b:
            return {"symbol": symbol, "error": msg_b, "quota_exceeded": True}

        out = _run_backtest_internal(
            symbol,
            start_date,
            end_date,
            signal_source=signal_source,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
            symbols=symbols,
        )
        if strategy_id and not out.get("error"):
            _save_backtest_to_strategy_market(strategy_id, strategy_name or strategy_id, out)
        return out
    except Exception as e:
        return {
            "symbol": symbol,
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "win_rate_pct": None,
            "profit_factor": None,
            "total_profit": None,
            "trade_count": None,
            "error": str(e),
        }


@router.post("/backtest/portfolio")
def run_backtest_portfolio_api(
    strategy_ids: List[str] = Body(
        ..., description="Strategy IDs from strategy_market / trade_signals"
    ),
    weights: Optional[List[float]] = Body(None),
    start_date: Optional[str] = Body(None),
    end_date: Optional[str] = Body(None),
    init_cash: float = Body(10000.0),
    fees: float = Body(0.001),
    slippage: float = Body(0.0),
) -> dict:
    """
    多策略组合回测：按 strategy_ids 与可选 weights 分配资金，各策略独立回测后按权重合并资金曲线与指标。
    """
    from datetime import datetime, timedelta
    import os
    import sys

    _root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    for _d in ["backtest-engine/src", "data-pipeline/src", "core/src"]:
        _p = os.path.join(_root, _d)
        if os.path.isdir(_p) and _p not in sys.path:
            sys.path.insert(0, _p)
    try:
        from backtest_engine.portfolio_backtest import run_portfolio_backtest

        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = start_date or (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
        out = run_portfolio_backtest(
            strategy_ids=strategy_ids,
            start_date=start,
            end_date=end,
            weights=weights,
            init_cash=init_cash,
            fees=fees,
            slippage=slippage,
        )
        return out
    except Exception as e:
        return {
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "per_strategy": [],
            "error": str(e),
        }


@router.get("/backtest/result")
def get_backtest_result(
    symbol: str = "000001.SZ",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    signal_source: str = "trade_signals",
    fees: float = 0.001,
    slippage: float = 0.0,
    symbols: Optional[str] = None,
) -> dict:
    """GET 回测结果：便于前端直接拉取资金曲线与指标，参数同 POST /backtest/run。"""
    try:
        return _run_backtest_internal(
            symbol,
            start_date,
            end_date,
            signal_source=signal_source,
            fees=fees,
            slippage=slippage,
            symbols=symbols,
        )
    except Exception as e:
        return {
            "symbol": symbol,
            "equity_curve": [],
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "win_rate_pct": None,
            "profit_factor": None,
            "total_profit": None,
            "trade_count": None,
            "error": str(e),
        }


@router.get("/portfolio/weights")
def get_portfolio_weights() -> dict:
    """当前组合权重：从 sim_positions + sim_account_snapshots 计算真实持仓与总资产。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"weights": {}, "capital": 0}
        conn = get_conn(read_only=False)
        try:
            # Total assets from latest snapshot
            snap = conn.execute(
                "SELECT total_assets FROM sim_account_snapshots ORDER BY snapshot_time DESC LIMIT 1"
            ).fetchone()
            capital = float(snap[0]) if snap and snap[0] else 0.0

            # Positions with market values
            rows = conn.execute(
                "SELECT code, qty, avg_price FROM sim_positions WHERE qty > 0"
            ).fetchall()
            weights = {}
            total_mv = 0.0
            for code, qty, avg_price in rows:
                mv = float(qty or 0) * float(avg_price or 0)
                total_mv += mv
            if total_mv > 0 and capital > 0:
                for code, qty, avg_price in rows:
                    mv = float(qty or 0) * float(avg_price or 0)
                    weights[str(code)] = round(mv / capital, 4)
            return {"weights": weights, "capital": capital}
        finally:
            conn.close()
    except Exception:
        return {"weights": {}, "capital": 0}


@router.get("/risk/status")
def risk_status() -> dict:
    """风控状态：实时检查回撤、仓位暴露、波动率。"""
    try:
        from risk_engine.drawdown_control import drawdown_ok
        from risk_engine.exposure_limit import exposure_ok
        from risk_engine.volatility_filter import volatility_ok as vol_ok
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"drawdown_ok": True, "exposure_ok": True, "volatility_ok": True}
        conn = get_conn(read_only=True)
        try:
            dd = drawdown_ok(conn)
            exp = exposure_ok(conn)
            vol = vol_ok(conn)
            return {"drawdown_ok": dd, "exposure_ok": exp, "volatility_ok": vol}
        finally:
            conn.close()
    except Exception:
        return {"drawdown_ok": True, "exposure_ok": True, "volatility_ok": True}


@router.get("/risk/rules")
def get_risk_rules() -> dict:
    """风控规则列表（从 risk_rules 表读取）。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return {"rules": []}
        conn = get_conn(read_only=False)
        load_rules, _, _ = _risk_engine_module()
        rules = load_rules(conn)
        conn.close()
        return {"rules": rules}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/rules")
def post_risk_rule(
    rule_type: str,
    value: float,
    enabled: bool = True,
    id: Optional[int] = None,
) -> dict:
    """新增或更新一条风控规则。rule_type: single_position_pct_max | max_drawdown_pct | max_exposure_pct。"""
    try:
        _, _, save_rule = _risk_engine_module()
        ok = save_rule(rule_type=rule_type, value=value, enabled=enabled, rule_id=id)
        return {"ok": ok}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/risk/check")
def post_risk_check(body: dict = Body(default={})) -> dict:
    """风控检查：body 含 positions（列表）、total_assets（float）、可选 equity_curve（列表），返回 pass 与 violations。"""
    try:
        _, evaluate, _ = _risk_engine_module()
        body = body or {}
        positions = body.get("positions") or []
        total_assets = float(body.get("total_assets") or 0)
        equity_curve = body.get("equity_curve")
        out = evaluate(positions=positions, total_assets=total_assets, equity_curve=equity_curve)
        return out
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
