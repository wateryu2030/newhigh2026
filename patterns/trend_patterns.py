# -*- coding: utf-8 -*-
"""
趋势类形态：多头排列、上升通道、突破平台、新高突破、均线粘合发散。
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


def detect_multi_ma_bull(
    df: pd.DataFrame,
    fast: int = 5,
    mid: int = 20,
    slow: int = 60,
) -> Tuple[pd.Series, pd.Series]:
    """
    多头排列：短期 > 中期 > 长期均线。
    返回 (是否多头排列, 强度 0~1)
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < slow:
        return pd.Series(dtype=bool), pd.Series(dtype=float)
    c = df["close"]
    ma_f = c.rolling(fast, min_periods=1).mean()
    ma_m = c.rolling(mid, min_periods=1).mean()
    ma_s = c.rolling(slow, min_periods=1).mean()
    bull = (ma_f > ma_m) & (ma_m > ma_s)
    strength = ((ma_f - ma_m) / (ma_m + 1e-10)).clip(-1, 1) * 0.5 + 0.5
    return bull, strength


def detect_uptrend_channel(
    df: pd.DataFrame,
    window: int = 20,
    slope_min: float = 0.001,
) -> Tuple[pd.Series, pd.Series]:
    """
    上升通道：高点、低点分别做线性回归，斜率均为正。
    返回 (是否上升通道, 通道斜率强度)
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < window:
        return pd.Series(dtype=bool), pd.Series(dtype=float)
    high = df["high"].rolling(window, min_periods=window).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == window else np.nan, raw=False
    )
    low = df["low"].rolling(window, min_periods=window).apply(
        lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == window else np.nan, raw=False
    )
    up_ch = (high > slope_min) & (low > slope_min)
    strength = (high + low) / 2
    strength = strength.fillna(0).clip(0, 0.02) / 0.02
    return up_ch, strength


def detect_breakout_platform(
    df: pd.DataFrame,
    window: int = 20,
    atr_mult: float = 0.5,
) -> pd.Series:
    """
    突破平台：收盘价突破 window 内最高价。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < window:
        return pd.Series(dtype=bool)
    high_n = df["high"].rolling(window, min_periods=1).max().shift(1)
    breakout = df["close"] > high_n
    return breakout


def detect_new_high_breakout(
    df: pd.DataFrame,
    window: int = 60,
) -> pd.Series:
    """
    新高突破：创 window 日内新高。
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < window:
        return pd.Series(dtype=bool)
    high_n = df["high"].rolling(window, min_periods=1).max().shift(1)
    return df["high"] >= high_n


def detect_ma_converge_divergence(
    df: pd.DataFrame,
    short: int = 5,
    long: int = 20,
    converge_threshold: float = 0.02,
    lookback: int = 5,
) -> Tuple[pd.Series, pd.Series]:
    """
    均线粘合后发散：短期与长期均线比值在 converge_threshold 内持续 lookback 根后分离。
    返回 (是否粘合后多头发散, 发散强度)
    """
    df = _ensure_ohlcv(df)
    if df is None or len(df) < long + lookback:
        return pd.Series(dtype=bool), pd.Series(dtype=float)
    c = df["close"]
    ma_s = c.rolling(short, min_periods=1).mean()
    ma_l = c.rolling(long, min_periods=1).mean()
    ratio = (ma_s / (ma_l + 1e-10) - 1).abs()
    converged = ratio.rolling(lookback, min_periods=lookback).max() <= converge_threshold
    diverged_bull = (ma_s > ma_l) & converged.shift(lookback).fillna(False)
    strength = (ma_s - ma_l) / (ma_l + 1e-10)
    return diverged_bull, strength


def detect_breakout(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    突破：收盘价突破 window 日最高（与设计文档示例一致）。
    """
    return detect_breakout_platform(df, window=window)
