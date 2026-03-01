# -*- coding: utf-8 -*-
"""
生产级缓存：日线等落 DuckDB，减少重复请求 AKShare。
与项目 database/duckdb_backend 复用或桥接。
"""
from __future__ import annotations
import os
from typing import Optional

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_cached_daily(symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """从本地库读日线，无则返回 None。"""
    try:
        import sys
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)
        from database.duckdb_backend import get_db_backend
        ob = symbol if "." in symbol else (symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE")
        db = get_db_backend()
        if not os.path.exists(getattr(db, "db_path", "")):
            return None
        df = db.get_daily_bars(ob, start_date, end_date)
        if df is None or len(df) == 0:
            return None
        df["date"] = df.index.astype(str).str[:10]
        return df
    except Exception:
        return None


def set_cached_daily(symbol: str, df: pd.DataFrame) -> bool:
    """写入日线到本地库。"""
    try:
        import sys
        if _ROOT not in sys.path:
            sys.path.insert(0, _ROOT)
        from database.duckdb_backend import get_db_backend
        ob = symbol if "." in symbol else (symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE")
        db = get_db_backend()
        db.add_daily_bars(ob, df)
        return True
    except Exception:
        return False
