"""
信号执行器：根据 trade_signals.signal_score 决定买卖（可接实盘/模拟）。
规则：signal_score > 0.7 执行买入，< 0.3 执行卖出。
"""

from __future__ import annotations

from typing import List, Tuple


def get_actionable_signals(
    buy_threshold: float = 0.7,
    sell_threshold: float = 0.3,
    limit: int = 20,
) -> Tuple[List[dict], List[dict]]:
    """从 trade_signals 表读取最近信号，拆成建议买入与建议卖出。"""
    buys, sells = [], []
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
        import os

        if not os.path.isfile(get_db_path()):
            return buys, sells
        conn = get_conn(read_only=True)
        df = conn.execute(
            """
            SELECT code, signal, confidence, target_price, stop_loss, signal_score, snapshot_time
            FROM trade_signals
            ORDER BY snapshot_time DESC
            LIMIT ?
        """,
            [limit * 2],
        ).fetchdf()
        conn.close()
        if df is None or df.empty:
            return buys, sells
        for _, row in df.iterrows():
            code = str(row.get("code", ""))
            score = float(row.get("signal_score") or 0)
            sig = row.get("signal") or "BUY"
            rec = {
                "code": code,
                "signal": sig,
                "confidence": float(row.get("confidence") or 0),
                "target_price": float(row.get("target_price") or 0),
                "stop_loss": float(row.get("stop_loss") or 0),
                "signal_score": score,
            }
            if score > buy_threshold and sig == "BUY":
                buys.append(rec)
            elif score < sell_threshold or sig == "SELL":
                sells.append(rec)
        return buys[:limit], sells[:limit]
    except Exception:
        return [], []


def execute_buy(code: str, confidence: float = 0.0, **kwargs) -> dict:
    """执行买入（当前为占位，可接实盘/模拟）。"""
    return {
        "ok": True,
        "action": "BUY",
        "code": code,
        "confidence": confidence,
        "message": "stub: execute_buy (no real order)",
        **kwargs,
    }


def execute_sell(code: str, confidence: float = 0.0, **kwargs) -> dict:
    """执行卖出（占位）。"""
    return {
        "ok": True,
        "action": "SELL",
        "code": code,
        "confidence": confidence,
        "message": "stub: execute_sell (no real order)",
        **kwargs,
    }


def run_signal_executor(
    buy_threshold: float = 0.7,
    sell_threshold: float = 0.3,
    dry_run: bool = True,
) -> dict:
    """
    根据 signal_score 执行买卖逻辑。
    dry_run=True 只返回将要执行的动作，不实际下单。
    """
    buys, sells = get_actionable_signals(buy_threshold=buy_threshold, sell_threshold=sell_threshold)
    actions = []
    if not dry_run:
        for b in buys:
            actions.append(execute_buy(b["code"], b.get("confidence", 0)))
        for s in sells:
            actions.append(execute_sell(s["code"], s.get("confidence", 0)))
    return {
        "dry_run": dry_run,
        "buy_candidates": [{"code": b["code"], "signal_score": b["signal_score"]} for b in buys],
        "sell_candidates": [{"code": s["code"], "signal_score": s["signal_score"]} for s in sells],
        "actions": actions,
    }
