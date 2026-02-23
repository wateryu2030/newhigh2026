# -*- coding: utf-8 -*-
"""
行情存储：DuckDB + Parquet 混合架构。
支持日线、分钟线、Parquet 分区、内存缓存，供策略与扫描器调用。
"""
from __future__ import annotations
import os
from typing import Dict, List, Optional
import pandas as pd

try:
    import duckdb
except ImportError:
    duckdb = None

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MarketDataStorage:
    """
    行情存储：DuckDB 主存储 + Parquet 分区备份 + 内存缓存。
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        parquet_root: Optional[str] = None,
        cache_size: int = 50,
    ):
        self.db_path = db_path or os.path.join(_ROOT, "data", "quant.duckdb")
        self.parquet_root = parquet_root or os.path.join(_ROOT, "data", "parquet")
        self.cache_size = cache_size
        self._cache: Dict[str, pd.DataFrame] = {}
        self._duck_conn: Optional[duckdb.DuckDBPyConnection] = None

    def _get_conn(self):
        if duckdb is None:
            raise ImportError("pip install duckdb")
        if getattr(self, "_duck_conn", None) is None or (hasattr(self._duck_conn, "closed") and self._duck_conn.closed):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._duck_conn = duckdb.connect(self.db_path)
            self._duck_conn.execute("PRAGMA threads=4")
        return self._duck_conn

    def _ensure_daily_table(self) -> None:
        c = self._get_conn()
        c.execute("""
            CREATE TABLE IF NOT EXISTS daily_data (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                PRIMARY KEY (symbol, date)
            )
        """)
        try:
            c.execute("CREATE INDEX IF NOT EXISTS idx_daily_symbol ON daily_data(symbol)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_data(date)")
        except Exception:
            pass

    def _ensure_minute_table(self) -> None:
        c = self._get_conn()
        c.execute("""
            CREATE TABLE IF NOT EXISTS minute_data (
                symbol VARCHAR NOT NULL,
                datetime TIMESTAMP NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume DOUBLE,
                amount DOUBLE,
                PRIMARY KEY (symbol, datetime)
            )
        """)

    def save_daily(self, df: pd.DataFrame, symbol_col: str = "symbol") -> None:
        """写入日线。DataFrame 需含 symbol/order_book_id, date/trade_date, open, high, low, close, volume[, amount]。"""
        if df is None or len(df) == 0:
            return
        self._ensure_daily_table()
        d = df.copy()
        if "date" not in d.columns and "trade_date" in d.columns:
            d["date"] = pd.to_datetime(d["trade_date"]).dt.strftime("%Y-%m-%d")
        if "symbol" not in d.columns and "order_book_id" in d.columns:
            d["symbol"] = d["order_book_id"].astype(str)
        for c in ("open", "high", "low", "close", "volume"):
            if c not in d.columns:
                d[c] = 0.0
        if "amount" not in d.columns:
            d["amount"] = d.get("total_turnover", 0.0)
        d = d[["symbol", "date", "open", "high", "low", "close", "volume", "amount"]].dropna(subset=["symbol", "date"])
        d["date"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
        c = self._get_conn()
        c.register("_daily_tmp", d)
        c.execute("""
            INSERT INTO daily_data SELECT * FROM _daily_tmp
            ON CONFLICT (symbol, date) DO UPDATE SET
            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
            volume=EXCLUDED.volume, amount=EXCLUDED.amount
        """)
        c.unregister("_daily_tmp")

    def save_minute(self, df: pd.DataFrame) -> None:
        """写入分钟线。"""
        if df is None or len(df) == 0:
            return
        self._ensure_minute_table()
        self._get_conn().register("_min_tmp", df)
        self._get_conn().execute("INSERT INTO minute_data SELECT * FROM _min_tmp")
        self._get_conn().unregister("_min_tmp")

    def load_daily(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """读取日线，优先内存缓存。"""
        key = f"{symbol}_{start_date}_{end_date}"
        if key in self._cache:
            return self._cache[key].copy()
        self._ensure_daily_table()
        sym = symbol.split(".")[0] if "." in symbol else symbol
        sql = "SELECT date, open, high, low, close, volume, amount FROM daily_data WHERE symbol = ?"
        params = [sym]
        if start_date:
            sql += " AND date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND date <= ?"
            params.append(end_date)
        sql += " ORDER BY date"
        c = self._get_conn()
        df = c.execute(sql, params).fetchdf()
        if len(df) > 0:
            df["trade_date"] = pd.to_datetime(df["date"])
            df = df.set_index("trade_date")
        while len(self._cache) >= self.cache_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = df.copy()
        return df

    def load_minute(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """读取分钟线。"""
        self._ensure_minute_table()
        sym = symbol.split(".")[0] if "." in symbol else symbol
        sql = "SELECT * FROM minute_data WHERE symbol = ?"
        params = [sym]
        if start:
            sql += " AND datetime >= ?"
            params.append(start)
        if end:
            sql += " AND datetime <= ?"
            params.append(end)
        sql += " ORDER BY datetime"
        return self._get_conn().execute(sql, params).fetchdf()

    def save_parquet_daily(self, symbol: str, df: pd.DataFrame) -> str:
        """按标的导出日线为 Parquet，路径 data/parquet/daily/symbol=xxx.parquet。"""
        os.makedirs(os.path.join(self.parquet_root, "daily"), exist_ok=True)
        path = os.path.join(self.parquet_root, "daily", f"symbol={symbol.replace('.', '_')}.parquet")
        df.to_parquet(path, index=True)
        return path

    def get_price(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        timeframe: str = "daily",
    ) -> pd.DataFrame:
        """统一接口：get_price(symbol, start, end)。"""
        if timeframe == "daily" or timeframe == "D":
            return self.load_daily(symbol, start, end)
        return self.load_minute(symbol, start, end)

    def update_realtime(self, data: dict) -> None:
        """实时行情缓存（可选）：可写入内存或 minute 表。"""
        key = data.get("symbol", "")
        if not key:
            return
        if key not in self._cache:
            self._cache[key] = pd.DataFrame()
        # 简单追加一行（实际可按需实现）
        pass


# 单例便于策略/扫描器复用
_storage: Optional[MarketDataStorage] = None


def get_market_storage() -> MarketDataStorage:
    global _storage
    if _storage is None:
        _storage = MarketDataStorage()
    return _storage
