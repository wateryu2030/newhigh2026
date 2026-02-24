# -*- coding: utf-8 -*-
"""
DuckDB 引擎：统一行情与交易日志读写，兼容 daily_bars / price_daily、trades 表。
"""
from __future__ import annotations
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_engine: Optional["DuckDBEngine"] = None


class DuckDBEngine:
    """封装 DuckDB：行情读取、交易记录写入。"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(_ROOT, "data", "quant.duckdb")
        self._connection = None

    def _get_conn(self):
        if getattr(self, "_connection", None) is not None and not getattr(self._connection, "closed", True):
            return self._connection
        import duckdb
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._connection = duckdb.connect(self.db_path)
        self._connection.execute("PRAGMA threads=4")
        return self._connection

    def get_daily_bars(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Optional[pd.DataFrame]:
        """读取日线。symbol 可为 order_book_id。"""
        if not os.path.exists(self.db_path):
            return None
        c = self._get_conn()
        sql = "SELECT trade_date AS date, order_book_id AS symbol, open, high, low, close, volume FROM daily_bars WHERE order_book_id = ?"
        params = [symbol]
        if start_date:
            sql += " AND trade_date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND trade_date <= ?"
            params.append(end_date)
        sql += " ORDER BY trade_date"
        try:
            df = c.execute(sql, params).fetchdf()
        except Exception:
            return None
        if len(df) == 0:
            return None
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        return df

    def get_stocks(self) -> List[tuple]:
        if not os.path.exists(self.db_path):
            return []
        try:
            df = self._get_conn().execute("SELECT order_book_id, symbol, name FROM stocks").fetchdf()
            return [tuple(row) for row in df.to_numpy().tolist()]
        except Exception:
            return []

    def _ensure_trades_table(self):
        c = self._get_conn()
        try:
            c.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    time TIMESTAMP,
                    symbol VARCHAR,
                    side VARCHAR,
                    qty DOUBLE,
                    price DOUBLE
                )
            """)
        except Exception:
            pass

    def log_trade(self, symbol: str, side: str, qty: float, price: float) -> None:
        self._ensure_trades_table()
        c = self._get_conn()
        c.execute(
            "INSERT INTO trades (time, symbol, side, qty, price) VALUES (?, ?, ?, ?, ?)",
            [datetime.now().isoformat(), symbol, side, qty, price],
        )

    def log_order(self, order: Dict[str, Any], action: str) -> None:
        if action == "place" and order.get("order_id"):
            self.log_trade(
                order.get("symbol", ""),
                order.get("side", ""),
                order.get("qty", 0),
                order.get("price", 0) or 0,
            )


def get_engine() -> DuckDBEngine:
    global _engine
    if _engine is None:
        try:
            from database.duckdb_backend import get_db_backend
            db = get_db_backend()
            path = getattr(db, "db_path", None)
            if path and os.path.exists(path):
                _engine = DuckDBEngine(path)
            else:
                _engine = DuckDBEngine()
        except Exception:
            _engine = DuckDBEngine()
    return _engine
