"""
信号执行器：根据 trade_signals.signal_score 决定买卖（可接实盘/模拟）。
规则：signal_score > 0.7 执行买入，< 0.3 执行卖出。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)


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
            _log.debug("DuckDB not found at %s, returning empty signals", get_db_path())
            return buys, sells
        conn = get_conn(read_only=False)
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
            sig = str(row.get("signal") or "BUY").upper()
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
        _log.info("actionable signals: %d buys, %d sells", len(buys), len(sells))
        return buys[:limit], sells[:limit]
    except Exception:
        _log.exception("Failed to read trade_signals")
        return [], []


def execute_buy(
    code: str,
    quantity: int = 100,
    confidence: float = 0.0,
    price: Optional[float] = None,
    dry_run: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    执行买入：dry_run=False 时通过 SimulatedBroker 下单到模拟盘。
    dry_run=True 只返回意向。
    """
    if dry_run:
        return {
            "ok": True,
            "action": "BUY",
            "code": code,
            "quantity": quantity,
            "confidence": confidence,
            "message": "dry_run: order not placed",
        }
    try:
        from execution_engine.brokers.registry import get_broker

        broker = get_broker()
        result = broker.submit_order(
            symbol=code,
            side="BUY",
            quantity=float(quantity),
            order_type="MARKET",
            price=price,
        )
        return {
            "ok": result.ok,
            "action": "BUY",
            "code": code,
            "quantity": quantity,
            "confidence": confidence,
            "order_id": result.order_id,
            "message": result.message or ("filled" if result.ok else "rejected"),
            **kwargs,
        }
    except Exception:
        _log.exception("execute_buy failed for %s", code)
        return {
            "ok": False,
            "action": "BUY",
            "code": code,
            "quantity": quantity,
            "confidence": confidence,
            "message": "execution error",
            **kwargs,
        }


def execute_sell(
    code: str,
    quantity: int = 100,
    confidence: float = 0.0,
    price: Optional[float] = None,
    dry_run: bool = True,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    执行卖出：dry_run=False 时通过 SimulatedBroker 下单到模拟盘。
    """
    if dry_run:
        return {
            "ok": True,
            "action": "SELL",
            "code": code,
            "quantity": quantity,
            "confidence": confidence,
            "message": "dry_run: order not placed",
        }
    try:
        from execution_engine.brokers.registry import get_broker

        broker = get_broker()
        result = broker.submit_order(
            symbol=code,
            side="SELL",
            quantity=float(quantity),
            order_type="MARKET",
            price=price,
        )
        return {
            "ok": result.ok,
            "action": "SELL",
            "code": code,
            "quantity": quantity,
            "confidence": confidence,
            "order_id": result.order_id,
            "message": result.message or ("filled" if result.ok else "rejected"),
            **kwargs,
        }
    except Exception:
        _log.exception("execute_sell failed for %s", code)
        return {
            "ok": False,
            "action": "SELL",
            "code": code,
            "quantity": quantity,
            "confidence": confidence,
            "message": "execution error",
            **kwargs,
        }


def run_signal_executor(
    buy_threshold: float = 0.7,
    sell_threshold: float = 0.3,
    dry_run: bool = True,
    lot_size: int = 100,
) -> Dict[str, Any]:
    """
    根据 signal_score 执行买卖逻辑。
    dry_run=True 只返回将要执行的动作，不实际下单。
    """
    buys, sells = get_actionable_signals(buy_threshold=buy_threshold, sell_threshold=sell_threshold)
    actions = []
    if not dry_run:
        for b in buys:
            res = execute_buy(
                b["code"],
                quantity=lot_size,
                confidence=b.get("confidence", 0),
                price=b.get("target_price") or None,
                dry_run=False,
            )
            actions.append(res)
        for s in sells:
            res = execute_sell(
                s["code"],
                quantity=lot_size,
                confidence=s.get("confidence", 0),
                price=s.get("stop_loss") or None,
                dry_run=False,
            )
            actions.append(res)
    return {
        "dry_run": dry_run,
        "buy_candidates": [{"code": b["code"], "signal_score": b["signal_score"]} for b in buys],
        "sell_candidates": [{"code": s["code"], "signal_score": s["signal_score"]} for s in sells],
        "actions": actions,
    }
