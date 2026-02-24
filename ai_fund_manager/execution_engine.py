# -*- coding: utf-8 -*-
"""
执行引擎：读取 trade_orders.json，将买卖指令交给现有交易系统执行。
不破坏现有交易代码，通过可选依赖对接 backend 的 OrderExecutor / OrderManager。
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _default_orders_path() -> str:
    return os.path.join(_ROOT, "output", "trade_orders.json")


def _get_price(symbol: str) -> Optional[float]:
    """从数据库取最新收盘价，用于将 target_value 转为股数。若无则返回 None。"""
    try:
        from database.duckdb_backend import get_db_backend
        from datetime import datetime, timedelta
        db = get_db_backend()
        if db is None:
            return None
        oid = symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE"
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        df = db.get_daily_bars(oid, start, end)
        if df is not None and len(df) > 0 and hasattr(df, "close"):
            return float(df["close"].iloc[-1])
        if df is not None and len(df) > 0:
            # index might be trade_date
            cols = getattr(df, "columns", [])
            if "close" in cols:
                return float(df["close"].iloc[-1])
    except Exception as e:
        logger.debug("Get price for %s: %s", symbol, e)
    return None


def _orders_to_trades(
    orders: List[Dict[str, Any]],
    capital: float = 1.0,
    get_price: Optional[Callable[[str], Optional[float]]] = None,
) -> List[Dict[str, Any]]:
    """
    将 orders（含 target_value / weight）转为可执行交易：symbol, side, qty, price。
    get_price(symbol) 返回最新价；若为 None 则用 1.0 占位（仅用于测试）。
    """
    get_price = get_price or _get_price
    trades = []
    for o in orders:
        symbol = (o.get("symbol") or "").strip()
        if not symbol:
            continue
        side = (o.get("side") or "BUY").upper()
        target_value = o.get("target_value")
        if target_value is None:
            weight = o.get("weight", 0)
            target_value = capital * weight
        price = get_price(symbol)
        if price is None or price <= 0:
            price = 1.0
            logger.warning("No price for %s, use 1.0 for qty calc", symbol)
        qty = int(round(target_value / price, 0))
        if qty <= 0:
            continue
        trades.append({
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "price": price,
            "target_value": target_value,
        })
    return trades


def execute_with_callback(
    orders_path: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    executor: Optional[Callable[[str, int, str, Optional[float]], Optional[Dict]]] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    加载订单并执行（或 dry_run 仅返回将要执行的交易列表）。
    :param orders_path: trade_orders.json 路径；若 payload 已提供可省略。
    :param payload: 若已读入 JSON，可直接传入，避免重复读文件。
    :param executor: (symbol, qty, side, price) -> order_result；None 时尝试 backend。
    :param dry_run: True 只返回计划交易，不真正下单。
    :return: {executed: int, failed: int, trades: [...], dry_run: bool}
    """
    result: Dict[str, Any] = {"executed": 0, "failed": 0, "trades": [], "dry_run": dry_run}
    if payload is None:
        path = orders_path or _default_orders_path()
        if not os.path.exists(path):
            logger.warning("Orders file not found: %s", path)
            return result
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as e:
            logger.exception("Load orders failed: %s", e)
            result["error"] = str(e)
            return result

    orders = payload.get("orders") or []
    capital = payload.get("capital", 1.0)
    trades = _orders_to_trades(orders, capital=capital)
    result["trades"] = trades

    if dry_run:
        result["executed"] = len(trades)
        return result

    if executor is None:
        try:
            from backend.trading.order_executor import OrderExecutor
            exec_instance = OrderExecutor()
            def _exec(s: str, q: int, side: str, p: Optional[float]):
                return exec_instance.place_order(symbol=s, qty=float(q), price=p, side=side)
            executor = _exec
        except Exception as e1:
            try:
                from backend.execution.order_manager import OrderManager
                mgr = OrderManager()
                def _exec(s: str, q: int, side: str, p: Optional[float]):
                    return mgr.place_order(s, q, side, p)
                executor = _exec
            except Exception as e2:
                logger.warning("No executor available: %s, %s", e1, e2)
                result["error"] = "No order executor available (backend not installed?)"
                return result

    for t in trades:
        try:
            out = executor(
                t["symbol"],
                t["qty"],
                t["side"],
                t.get("price"),
            )
            if out:
                result["executed"] += 1
            else:
                result["failed"] += 1
        except Exception as e:
            logger.exception("Execute %s %s %s: %s", t["symbol"], t["side"], t["qty"], e)
            result["failed"] += 1

    return result


def run(orders_path: Optional[str] = None, dry_run: bool = True) -> Dict[str, Any]:
    """
    便捷入口：从默认路径执行订单。
    :param orders_path: 可选，默认 output/trade_orders.json。
    :param dry_run: 默认 True，仅打印不真实下单。
    """
    return execute_with_callback(orders_path=orders_path, dry_run=dry_run)
