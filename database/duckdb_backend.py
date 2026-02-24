# -*- coding: utf-8 -*-
"""
DuckDB 数据后端：平台唯一数据库，与旧 StockDatabase 接口兼容。
"""
from __future__ import annotations
import os
from typing import List, Optional, Tuple
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _duckdb_path() -> str:
    return os.path.join(_ROOT, "data", "quant.duckdb")


def get_db_backend():
    """返回平台唯一数据后端（DuckDB）。"""
    return DuckDBBackend()


class DuckDBBackend:
    """
    与 database.db_schema.StockDatabase 兼容的接口，底层用 DuckDB。
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _duckdb_path()
        self._connection = None

    def _get_conn(self):
        if self._connection is not None and not getattr(self._connection, "closed", True):
            return self._connection
        try:
            import duckdb
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._connection = duckdb.connect(self.db_path)
            self._connection.execute("PRAGMA threads=4")
            self._ensure_schema()
            return self._connection
        except ImportError:
            raise ImportError("请安装 duckdb: pip install duckdb")

    def _ensure_schema(self):
        """确保 stocks / daily_bars 表存在（空库首次使用时创建）。"""
        c = self._connection
        c.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                order_book_id VARCHAR PRIMARY KEY,
                symbol VARCHAR NOT NULL,
                name VARCHAR,
                market VARCHAR,
                listed_date VARCHAR,
                de_listed_date VARCHAR,
                type VARCHAR,
                updated_at TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_bars (
                order_book_id VARCHAR NOT NULL,
                trade_date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                total_turnover DOUBLE,
                adjust_factor DOUBLE DEFAULT 1.0,
                PRIMARY KEY (order_book_id, trade_date)
            )
        """)
        for idx_sql in (
            "CREATE INDEX IF NOT EXISTS idx_daily_bars_order_book_id ON daily_bars(order_book_id)",
            "CREATE INDEX IF NOT EXISTS idx_daily_bars_trade_date ON daily_bars(trade_date)",
        ):
            try:
                c.execute(idx_sql)
            except Exception:
                pass

    def get_daily_bars(
        self,
        order_book_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """与 StockDatabase.get_daily_bars 一致：返回 index=trade_date, columns=open,high,low,close,volume,total_turnover。"""
        if not os.path.exists(self.db_path):
            return pd.DataFrame()
        c = self._get_conn()
        sql = "SELECT trade_date, open, high, low, close, volume, total_turnover FROM daily_bars WHERE order_book_id = ?"
        params = [order_book_id]
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
            return pd.DataFrame()
        if len(df) == 0:
            return pd.DataFrame()
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date")
        return df

    def get_stocks(self) -> List[Tuple]:
        """与 StockDatabase.get_stocks 一致。"""
        if not os.path.exists(self.db_path):
            return []
        try:
            df = self._get_conn().execute("SELECT order_book_id, symbol, name FROM stocks").fetchdf()
            return [tuple(row) for row in df.to_numpy().tolist()]
        except Exception:
            return []

    def get_daily_bars_count(self) -> int:
        """日线表总条数，供 db_stats 等使用，避免重复打开同一 DuckDB 文件。"""
        if not os.path.exists(self.db_path):
            return 0
        try:
            r = self._get_conn().execute("SELECT COUNT(*) FROM daily_bars").fetchone()
            return int(r[0]) if r else 0
        except Exception:
            return 0

    def add_daily_bars(self, order_book_id: str, bars_df: pd.DataFrame) -> None:
        """写入日线。bars_df 可为中文列名 日期/开盘/最高/最低/收盘/成交量/成交额。"""
        if bars_df is None or len(bars_df) == 0:
            return
        col_map = {"日期": "trade_date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume", "成交额": "total_turnover"}
        d = bars_df.copy()
        for cn, en in col_map.items():
            if cn in d.columns and en not in d.columns:
                d[en] = d[cn]
        d["order_book_id"] = order_book_id
        if "trade_date" not in d.columns and "日期" in d.columns:
            d["trade_date"] = pd.to_datetime(d["日期"]).dt.strftime("%Y-%m-%d")
        d["total_turnover"] = d.get("total_turnover", d.get("成交额", 0))
        d["adjust_factor"] = 1.0
        cols = ["order_book_id", "trade_date", "open", "high", "low", "close", "volume", "total_turnover", "adjust_factor"]
        for c in cols:
            if c not in d.columns:
                d[c] = 0.0
        d = d[cols]
        c = self._get_conn()
        c.register("_bars", d)
        c.execute("""
            INSERT INTO daily_bars SELECT * FROM _bars
            ON CONFLICT (order_book_id, trade_date) DO UPDATE SET
            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
            volume=EXCLUDED.volume, total_turnover=EXCLUDED.total_turnover
        """)
        c.unregister("_bars")

    def add_stock(
        self,
        order_book_id: str,
        symbol: str,
        name: Optional[str] = None,
        market: str = "CN",
        listed_date: Optional[str] = None,
        de_listed_date: Optional[str] = None,
        type: str = "CS",
    ) -> None:
        """添加或更新股票基本信息，与 StockDatabase.add_stock 兼容。"""
        from datetime import datetime
        c = self._get_conn()
        now = datetime.now().isoformat()[:19]
        name_val = name if name else symbol
        c.execute("DELETE FROM stocks WHERE order_book_id = ?", [order_book_id])
        try:
            c.execute("""
                INSERT INTO stocks (order_book_id, symbol, name, market, listed_date, de_listed_date, type, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [order_book_id, symbol, name_val, market, listed_date, de_listed_date, type, now])
        except Exception:
            c.execute(
                "INSERT INTO stocks (order_book_id, symbol, name) VALUES (?, ?, ?)",
                [order_book_id, symbol, name_val],
            )


