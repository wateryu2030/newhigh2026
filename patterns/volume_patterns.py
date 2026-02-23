# -*- coding: utf-8 -*-
"""
量价类形态：放量突破、缩量回踩、主力吸筹。
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, Tuple


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) < 2:
        return df
    for col in ("open", "high", "low", "close", "volume"):
        if col not in df.columns:
            return df
    return df


def detect_volume_breakout(
    df: pd.DataFrame,
    price_window: int = 20,
    volume_ma_window: int = 5,
    volume_mult: float = 1.5,
) -> pd.Series:
    """
    放量突破：价格突破 platform，且成交量 > volume_ma * volume_mult。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < max(price_window, volume_ma_window):
        return pd.Series(dtype=bool)
    high_n = df["high"].rolling(price_window, min_periods=1).max().shift(1)
    price_break = df["close"] > high_n
    vol_ma = df["volume"].rolling(volume_ma_window, min_periods=1).mean()
    vol_break = df["volume"] >= vol_ma * volume_mult
    return price_break & vol_break


def detect_volume_pullback(
    df: pd.DataFrame,
    ma_fast: int = 5,
    ma_slow: int = 20,
    volume_ratio_max: float = 0.7,
) -> pd.Series:
    """
    缩量回踩：价格在均线上方或附近，成交量缩至均量以下（volume_ratio_max * 均量）。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < ma_slow:
        return pd.Series(dtype=bool)
    c = df["close"]
    v = df["volume"]
    ma_f = c.rolling(ma_fast, min_periods=1).mean()
    ma_s = c.rolling(ma_slow, min_periods=1).mean()
    vol_ma = v.rolling(ma_slow, min_periods=1).mean()
    above_ma = c >= ma_s * 0.98
    low_vol = v <= (vol_ma * volume_ratio_max)
    return above_ma & low_vol


def detect_volume_accumulation(
    df: pd.DataFrame,
    window: int = 20,
    price_up_pct: float = 0.02,
    volume_increase: float = 1.2,
) -> pd.Series:
    """
    主力吸筹：阶段涨幅不大但成交量明显放大（价稳量增）。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < window:
        return pd.Series(dtype=bool)
    c = df["close"]
    v = df["volume"]
    price_chg = (c - c.shift(window)) / (c.shift(window) + 1e-10)
    vol_ratio = v.rolling(window).mean() / (v.rolling(window * 2).mean().shift(window) + 1e-10)
    mild_up = (price_chg > 0) & (price_chg <= price_up_pct)
    vol_up = vol_ratio >= volume_increase
    return mild_up & vol_up
