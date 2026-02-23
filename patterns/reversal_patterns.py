# -*- coding: utf-8 -*-
"""
反转类形态：双底、V反、超跌反弹。
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from typing import Optional, Tuple


def _ensure_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or len(df) < 2:
        return df
    for col in ("open", "high", "low", "close"):
        if col not in df.columns:
            return df
    return df


def detect_double_bottom(
    df: pd.DataFrame,
    window: int = 30,
    tolerance: float = 0.03,
) -> pd.Series:
    """
    双底：在 window 内出现两次相近的低点，且当前收盘已反弹。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < window:
        return pd.Series(dtype=bool)
    low = df["low"]
    close = df["close"]
    out = pd.Series(False, index=df.index)
    for i in range(window, len(df)):
        w = low.iloc[i - window : i]
        bot = w.min()
        # 至少两根 K 线低点在 tolerance 内
        near_bottom = (w <= bot * (1 + tolerance)).sum()
        if near_bottom < 2:
            continue
        if close.iloc[i] > bot * (1 + tolerance):
            out.iloc[i] = True
    return out


def detect_v_reversal(
    df: pd.DataFrame,
    lookback: int = 10,
    drop_pct: float = 0.05,
    bounce_pct: float = 0.03,
) -> pd.Series:
    """
    V型反转：lookback 内跌幅超过 drop_pct，且最近一根反弹超过 bounce_pct。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < lookback + 1:
        return pd.Series(dtype=bool)
    close = df["close"]
    low_in = close.rolling(lookback, min_periods=lookback).min().shift(1)
    drop = (close.shift(lookback - 1) - low_in) / (close.shift(lookback - 1) + 1e-10)
    bounce = (close - close.shift(1)) / (close.shift(1) + 1e-10)
    v_rev = (drop >= drop_pct) & (bounce >= bounce_pct)
    return v_rev


def detect_oversold_bounce(
    df: pd.DataFrame,
    rsi_period: int = 14,
    rsi_oversold: float = 30,
    confirm_bars: int = 2,
) -> pd.Series:
    """
    超跌反弹：RSI 进入超卖后回升。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < rsi_period + confirm_bars:
        return pd.Series(dtype=bool)
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    avg_gain = gain.rolling(rsi_period, min_periods=1).mean()
    avg_loss = loss.rolling(rsi_period, min_periods=1).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    was_oversold = rsi.shift(confirm_bars) <= rsi_oversold
    now_rising = rsi > rsi.shift(1)
    return was_oversold & now_rising
