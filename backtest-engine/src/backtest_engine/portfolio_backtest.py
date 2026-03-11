"""
多策略组合回测：按策略分配权重，各策略独立回测后按权重合并资金曲线与指标。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .run_with_db import run_backtest_multi_from_db, _metrics_from_equity_curve
from .strategy_allocator import allocate_weights, get_symbols_for_strategy


def run_portfolio_backtest(
    strategy_ids: List[str],
    start_date: str,
    end_date: str,
    weights: Optional[List[float]] = None,
    signal_source: str = "trade_signals",
    init_cash: float = 10000.0,
    fees: float = 0.001,
    slippage: float = 0.0,
    conn: Any = None,
) -> Dict[str, Any]:
    """
    多策略组合回测。
    strategy_ids: 策略 ID 列表（对应 strategy_market / trade_signals.strategy_id）。
    weights: 可选，与 strategy_ids 等长；None 表示等权。
    对每个策略：取该策略有信号的标的列表，跑多标的回测（run_backtest_multi_from_db + strategy_id），
    再按权重合并各策略资金曲线（同日期加权求和），并重算组合的 total_return、max_drawdown、sharpe_ratio。
    返回格式与 run_backtest_from_db 一致。
    """
    result = {
        "equity_curve": [],
        "sharpe_ratio": None,
        "max_drawdown": None,
        "total_return": None,
        "win_rate_pct": None,
        "profit_factor": None,
        "total_profit": None,
        "trade_count": None,
        "error": None,
        "per_strategy": [],
    }
    if not strategy_ids:
        result["error"] = "no_strategy_ids"
        return result

    allocated = allocate_weights(strategy_ids, weights)
    if not allocated:
        result["error"] = "allocator_failed"
        return result

    close_conn = conn is None
    if conn is None:
        try:
            from data_pipeline.storage.duckdb_manager import get_conn
            conn = get_conn(read_only=False)
        except Exception:
            result["error"] = "no_db"
            return result

    per_cash = init_cash / len(allocated)
    curves: List[Dict[str, Any]] = []
    try:
        for sid, weight in allocated:
            symbols = get_symbols_for_strategy(sid, conn=conn)
            if not symbols:
                result["per_strategy"].append({
                    "strategy_id": sid,
                    "weight": weight,
                    "equity_curve": [],
                    "error": "no_signals",
                })
                continue
            r = run_backtest_multi_from_db(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                signal_source=signal_source,
                strategy_id=sid,
                init_cash=per_cash,
                fees=fees,
                slippage=slippage,
                conn=conn,
            )
            result["per_strategy"].append({
                "strategy_id": sid,
                "weight": weight,
                "equity_curve": r.get("equity_curve") or [],
                "sharpe_ratio": r.get("sharpe_ratio"),
                "max_drawdown": r.get("max_drawdown"),
                "total_return": r.get("total_return"),
                "total_profit": r.get("total_profit"),
                "trade_count": r.get("trade_count"),
                "error": r.get("error"),
            })
            curves.append((weight, r.get("equity_curve") or []))

        if not curves:
            result["error"] = "no_ohlcv_or_signals"
            if close_conn and conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
            return result

        # 按日期加权合并资金曲线
        by_date: Dict[str, float] = {}
        for w, eq in curves:
            for point in eq:
                d = point.get("date") or ""
                v = float(point.get("value") or 0)
                by_date[d] = by_date.get(d, 0) + w * v
        result["equity_curve"] = [{"date": d, "value": v} for d, v in sorted(by_date.items())]
        agg = _metrics_from_equity_curve(result["equity_curve"])
        result["total_return"] = agg.get("total_return")
        result["max_drawdown"] = agg.get("max_drawdown")
        result["sharpe_ratio"] = agg.get("sharpe_ratio")
        result["total_profit"] = sum(
            p.get("total_profit") or 0 for p in result["per_strategy"]
        )
        result["trade_count"] = sum(
            p.get("trade_count") or 0 for p in result["per_strategy"]
        )
        wrs = [p.get("win_rate_pct") for p in result["per_strategy"] if p.get("win_rate_pct") is not None]
        pfs = [p.get("profit_factor") for p in result["per_strategy"] if p.get("profit_factor") is not None]
        result["win_rate_pct"] = sum(wrs) / len(wrs) if wrs else None
        result["profit_factor"] = sum(pfs) / len(pfs) if pfs else None
    finally:
        if close_conn and conn is not None:
            try:
                conn.close()
            except Exception:
                pass

    return result
