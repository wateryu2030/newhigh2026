# -*- coding: utf-8 -*-
"""
交易日志写入 DuckDB：trade_logs、orders、positions 表。
使用项目 data/quant.duckdb 或单独 trading.duckdb，此处用同一库并加表。
"""
from __future__ import annotations
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_conn():
    """使用项目 DuckDB；若不存在则用 data/trading.duckdb。"""
    try:
        from database.duckdb_backend import get_db_backend
        db = get_db_backend()
        path = getattr(db, "db_path", None)
        if path and os.path.exists(path):
            return db._get_conn()
    except Exception:
        pass
    path = os.path.join(_ROOT, "data", "trading.duckdb")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    import duckdb
    return duckdb.connect(path)


def _ensure_tables(conn) -> None:
    """创建 trade_logs、orders、positions 表（若不存在）。"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_logs (
            id INTEGER PRIMARY KEY,
            ts VARCHAR,
            symbol VARCHAR,
            action VARCHAR,
            signal_confidence DOUBLE,
            risk_ok BOOLEAN,
            position_pct DOUBLE,
            order_id VARCHAR,
            msg VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            order_id VARCHAR,
            symbol VARCHAR,
            qty DOUBLE,
            price DOUBLE,
            side VARCHAR,
            status VARCHAR,
            ts VARCHAR,
            extra VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY,
            ts VARCHAR,
            symbol VARCHAR,
            qty DOUBLE,
            avg_price DOUBLE,
            market_value DOUBLE,
            weight DOUBLE
        )
    """)


def log_trade(
    symbol: str,
    action: str,
    signal_confidence: float = 0,
    risk_ok: bool = True,
    position_pct: float = 0,
    order_id: Optional[str] = None,
    msg: str = "",
) -> None:
    """写入一条交易日志到 trade_logs。"""
    conn = _get_conn()
    _ensure_tables(conn)
    ts = datetime.now().isoformat()
    try:
        r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM trade_logs").fetchone()
        nid = r[0] if r else 1
        conn.execute(
            "INSERT INTO trade_logs (id, ts, symbol, action, signal_confidence, risk_ok, position_pct, order_id, msg) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [nid, ts, symbol, action, signal_confidence, risk_ok, position_pct, order_id or "", msg],
        )
    finally:
        conn.close()


def log_order(order: Dict[str, Any], action: str = "place") -> None:
    """写入或更新 orders 表。"""
    conn = _get_conn()
    _ensure_tables(conn)
    ts = datetime.now().isoformat()
    try:
        if action == "place":
            r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM orders").fetchone()
            nid = r[0] if r else 1
            conn.execute(
                "INSERT INTO orders (id, order_id, symbol, qty, price, side, status, ts, extra) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    nid,
                    order.get("order_id", ""),
                    order.get("symbol", ""),
                    order.get("qty", 0),
                    order.get("price"),
                    order.get("side", ""),
                    order.get("status", "submitted"),
                    ts,
                    "",
                ],
            )
        elif action == "cancel":
            conn.execute("UPDATE orders SET status = 'cancelled', extra = ? WHERE order_id = ?", [ts, order.get("order_id", "")])
    finally:
        conn.close()


def log_positions(positions: List[Dict[str, Any]]) -> None:
    """批量写入当日快照到 positions。"""
    conn = _get_conn()
    _ensure_tables(conn)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        for p in positions:
            r = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM positions").fetchone()
            nid = r[0] if r else 1
            conn.execute(
                "INSERT INTO positions (id, ts, symbol, qty, avg_price, market_value, weight) VALUES (?, ?, ?, ?, ?, ?, ?)",
                [nid, ts, p.get("symbol", ""), p.get("qty", 0), p.get("avg_price", 0), p.get("market_value", 0), p.get("weight", 0)],
            )
    finally:
        conn.close()
