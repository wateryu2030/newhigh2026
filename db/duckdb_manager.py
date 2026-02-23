# -*- coding: utf-8 -*-
"""
DuckDB 连接管理：自动初始化、DataFrame 读写、SQL、Parquet。
支持量化场景：历史行情、因子、回测结果、扫描缓存。
"""
from __future__ import annotations
import os
from typing import Any, List, Optional
import pandas as pd

try:
    import duckdb
except ImportError:
    duckdb = None

from .performance import apply_duckdb_performance


class DuckDBManager:
    """
    DuckDB 连接管理。
    - 自动初始化数据库与表结构
    - execute / query_df / insert_df
    - Parquet 读写
    """

    def __init__(self, db_path: str = "data/quant.duckdb"):
        if duckdb is None:
            raise ImportError("请安装 duckdb: pip install duckdb")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
        self.db_path = os.path.abspath(db_path)
        self.conn = duckdb.connect(self.db_path)
        apply_duckdb_performance(self.conn)
        self._init_schema()

    def _init_schema(self) -> None:
        """创建量化常用表（若不存在）。"""
        self.conn.execute("""
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
        self.conn.execute("""
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
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trading_calendar (
                trade_date DATE PRIMARY KEY,
                is_trading INTEGER DEFAULT 1
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY,
                strategy_id VARCHAR,
                symbol VARCHAR,
                start_date DATE,
                end_date DATE,
                total_return DOUBLE,
                max_drawdown DOUBLE,
                sharpe DOUBLE,
                trade_count INTEGER,
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scan_results (
                id INTEGER PRIMARY KEY,
                symbol VARCHAR,
                scan_date DATE,
                signal VARCHAR,
                score DOUBLE,
                strategy_id VARCHAR,
                created_at TIMESTAMP DEFAULT current_timestamp
            )
        """)
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_order ON daily_bars(order_book_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_date ON daily_bars(trade_date)")
        except Exception:
            pass

    def execute(self, sql: str, params: Optional[list] = None) -> Any:
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    def query_df(self, sql: str, params: Optional[list] = None) -> pd.DataFrame:
        """执行 SQL 返回 DataFrame。"""
        if params:
            return self.conn.execute(sql, params).fetchdf()
        return self.conn.execute(sql).fetchdf()

    def insert_df(self, table: str, df: pd.DataFrame, replace: bool = True) -> None:
        """
        将 DataFrame 写入表。replace=True 时对 daily_bars 使用 ON CONFLICT 覆盖。
        """
        if df is None or len(df) == 0:
            return
        self.conn.register("_tmp_df", df)
        if replace and table == "daily_bars" and "order_book_id" in df.columns and "trade_date" in df.columns:
            self.conn.execute("""
                INSERT INTO daily_bars SELECT * FROM _tmp_df
                ON CONFLICT (order_book_id, trade_date) DO UPDATE SET
                open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
                volume=EXCLUDED.volume, total_turnover=EXCLUDED.total_turnover, adjust_factor=EXCLUDED.adjust_factor
            """)
        else:
            self.conn.execute(f"INSERT INTO {table} SELECT * FROM _tmp_df")
        self.conn.unregister("_tmp_df")

    def save_parquet(self, table: str, path: str) -> None:
        """将表导出为 Parquet。"""
        path_abs = os.path.abspath(path)
        self.conn.execute(f"COPY (SELECT * FROM {table}) TO '{path_abs}' (FORMAT PARQUET)")

    def read_parquet(self, path: str) -> pd.DataFrame:
        """读取 Parquet 为 DataFrame。"""
        path_abs = os.path.abspath(path)
        return self.conn.execute(f"SELECT * FROM read_parquet('{path_abs}')").fetchdf()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "DuckDBManager":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
