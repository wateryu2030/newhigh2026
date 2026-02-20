# -*- coding: utf-8 -*-
"""
多周期 K 线：日线 / 周线 / 月线 重采样。
"""
import pandas as pd
from typing import Optional

# 前端/API 周期标识 -> pandas resample 规则
TIMEFRAME_MAP = {
    "D": "1D",
    "日": "1D",
    "日线": "1D",
    "W": "1W",
    "周": "1W",
    "周线": "1W",
    "M": "1M",
    "月": "1M",
    "月线": "1M",
}


def normalize_timeframe(tf: str) -> str:
    """统一为 D / W / M。"""
    if not tf:
        return "D"
    t = (tf or "").strip().upper()
    if t in ("D", "W", "M"):
        return t
    if t in ("日", "日线") or "DAY" in t:
        return "D"
    if t in ("周", "周线") or "WEEK" in t:
        return "W"
    if t in ("月", "月线") or "MONTH" in t:
        return "M"
    return "D"


def resample_kline(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    将日线 K 线重采样为指定周期。

    :param df: 日线 DataFrame，index 为 DatetimeIndex，列含 open, high, low, close, volume
    :param timeframe: "D" | "W" | "M"（日/周/月）
    :return: 重采样后的 DataFrame，列同上；若无数据返回空 DataFrame
    """
    if df is None or len(df) == 0:
        return pd.DataFrame()
    tf = normalize_timeframe(timeframe)
    if tf == "D":
        out = df.copy()
        if "date" not in out.columns and out.index is not None:
            out["date"] = out.index.astype(str).str[:10]
        return out
    rule = TIMEFRAME_MAP.get(tf, "1D")
    if rule == "1D":
        out = df.copy()
        if "date" not in out.columns and out.index is not None:
            out["date"] = out.index.astype(str).str[:10]
        return out
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        if "trade_date" in df.columns:
            df = df.set_index(pd.to_datetime(df["trade_date"]))
        elif "date" in df.columns:
            df = df.set_index(pd.to_datetime(df["date"]))
        else:
            return df
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    if "total_turnover" in df.columns:
        agg["total_turnover"] = "sum"
    res = df.resample(rule).agg(agg).dropna(how="all")
    res = res[res["close"].notna()]
    res["date"] = res.index.astype(str).str[:10]
    return res
