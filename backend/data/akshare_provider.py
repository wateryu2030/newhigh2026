# -*- coding: utf-8 -*-
"""
生产级数据提供：AKShare 日线拉取，可配合 cache_db 做本地缓存。
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd


def get_daily_bars(
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """
    从 AKShare 拉取日线。symbol 为 6 位代码。
    返回 DataFrame 含 close, high, low, open, volume（或中文列名）。
    """
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    start_ymd = start_date.replace("-", "")[:8]
    end_ymd = end_date.replace("-", "")[:8]
    code = symbol.split(".")[0] if "." in symbol else symbol
    try:
        import akshare as ak
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_ymd, end_date=end_ymd, adjust=adjust)
    except Exception:
        return pd.DataFrame()
    if df is None or len(df) == 0:
        return pd.DataFrame()
    df = df.rename(columns={
        "日期": "date", "开盘": "open", "收盘": "close", "最高": "high", "最低": "low", "成交量": "volume",
    })
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def get_batch_daily(
    symbols: List[str],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """批量拉取，返回 { symbol: df }。"""
    out = {}
    for s in symbols:
        df = get_daily_bars(s, start_date, end_date)
        if df is not None and len(df) > 0:
            out[s] = df
    return out
