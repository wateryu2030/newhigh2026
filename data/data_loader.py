# -*- coding: utf-8 -*-
"""
数据加载统一入口：K 线可从 AKShare 或本地数据库加载，便于回测/扫描复用。
"""
import os
from typing import Optional
import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_kline(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    source: str = "database",
) -> pd.DataFrame:
    """
    加载 K 线：source=database 时从 SQLite 读，source=akshare 时从 AKShare 拉取。
    :param symbol: 如 000001 或 000001.XSHE
    :param start_date: YYYY-MM-DD
    :param end_date: YYYY-MM-DD
    :param source: database | akshare
    """
    code = symbol.split(".")[0] if "." in symbol else symbol
    if source == "akshare":
        from .stock_pool import load_kline as akshare_load
        start_ymd = (start_date or "").replace("-", "")[:8]
        end_ymd = (end_date or "").replace("-", "")[:8]
        return akshare_load(code, "daily", "qfq", start_ymd, end_ymd)
    # database（DuckDB）
    try:
        import sys
        sys.path.insert(0, _ROOT)
        from database.duckdb_backend import get_db_backend
        order_book_id = symbol if "." in symbol else (code + ".XSHG" if code.startswith("6") else code + ".XSHE")
        db = get_db_backend()
        db_path = getattr(db, "db_path", os.path.join(_ROOT, "data", "quant.duckdb"))
        if not os.path.exists(db_path):
            return pd.DataFrame()
        df = db.get_daily_bars(order_book_id, start_date, end_date)
        if df is None or len(df) == 0:
            return pd.DataFrame()
        df["date"] = df.index.astype(str).str[:10]
        return df
    except Exception:
        return pd.DataFrame()
