#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型定义 - 统一使用 DuckDB。

本模块保留 StockDatabase 类名以兼容旧引用，实际实现委托给 database.duckdb_backend。
平台唯一数据库为 data/quant.duckdb，不再使用 SQLite。
"""
from __future__ import annotations
import os
from typing import List, Optional, Tuple
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_backend():
    from database.duckdb_backend import get_db_backend
    return get_db_backend()


class StockDatabase:
    """
    股票数据库管理类（委托给 DuckDB 后端）。
    新代码请直接使用 database.duckdb_backend.get_db_backend()。
    """

    def __init__(self, db_path: Optional[str] = None):
        # db_path 仅保留兼容，实际使用 quant.duckdb
        self.db_path = db_path or os.path.join(_ROOT, "data", "quant.duckdb")
        self._backend = _get_backend()

    def init_database(self):
        """确保 DuckDB 表结构存在（由后端首次连接时自动创建）。"""
        self._backend._get_conn()

    def add_stock(
        self,
        order_book_id: str,
        symbol: str,
        name: Optional[str] = None,
        market: str = "CN",
        listed_date: Optional[str] = None,
        de_listed_date: Optional[str] = None,
        type: str = "CS",
    ):
        self._backend.add_stock(
            order_book_id, symbol, name=name, market=market,
            listed_date=listed_date, de_listed_date=de_listed_date, type=type,
        )

    def add_daily_bars(self, order_book_id: str, bars_df: pd.DataFrame):
        self._backend.add_daily_bars(order_book_id, bars_df)

    def get_daily_bars(
        self,
        order_book_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        return self._backend.get_daily_bars(order_book_id, start_date, end_date)

    def get_stocks(self) -> List[Tuple]:
        return self._backend.get_stocks()

    def add_trading_dates(self, dates: List[str]):
        """DuckDB 当前未使用交易日历表，保留接口为空实现。"""
        pass

    def get_trading_dates(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[str]:
        """DuckDB 当前未使用交易日历表，返回空列表。"""
        return []
