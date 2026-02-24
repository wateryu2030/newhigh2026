# -*- coding: utf-8 -*-
"""
因子工程：从 DuckDB 读取行情，计算技术指标，输出特征 DataFrame。
生产级，带类型注解与注释。
"""
from __future__ import annotations
from typing import Optional

import numpy as np
import pandas as pd


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return (100 - (100 / (1 + rs))).fillna(50)


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    从 OHLCV 日线构建特征表。
    指标：MA5/MA10/MA20, RSI, MACD, ATR, Momentum, Volume Ratio。
    要求 df 含 open, high, low, close, volume；index 可为 trade_date。
    """
    if df is None or len(df) < 60:
        return pd.DataFrame()
    df = df.copy()
    if isinstance(df.index, pd.DatetimeIndex):
        df["date"] = df.index.astype(str).str[:10]
    close = df["close"].astype(float)
    high = df["high"].astype(float) if "high" in df.columns else close
    low = df["low"].astype(float) if "low" in df.columns else close
    volume = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1.0, index=df.index)

    df["MA5"] = close.rolling(5, min_periods=1).mean()
    df["MA10"] = close.rolling(10, min_periods=1).mean()
    df["MA20"] = close.rolling(20, min_periods=1).mean()
    macd_line, signal_line, hist = _macd(close)
    df["MACD"] = macd_line
    df["MACD_signal"] = signal_line
    df["MACD_hist"] = hist
    df["RSI"] = _rsi(close, 14)
    df["ATR"] = _atr(high, low, close, 14)
    df["Momentum"] = close.pct_change(20).fillna(0)
    vol_ma = volume.rolling(20, min_periods=1).mean().replace(0, np.nan)
    df["Volume_Ratio"] = (volume / vol_ma).fillna(1.0)
    df["return_1d"] = close.pct_change(1).fillna(0)
    df["volatility_20"] = df["return_1d"].rolling(20, min_periods=2).std().fillna(0)
    df["forward_return_5d"] = close.shift(-5) / close - 1.0
    df = df.dropna(subset=["MA20", "MACD", "RSI", "ATR"])
    return df


def load_and_build_features(
    symbol: str,
    start_date: str,
    end_date: str,
    db_engine,
) -> pd.DataFrame:
    """从 DuckDB 引擎读取该标的日线并构建特征。"""
    df = db_engine.get_daily_bars(symbol, start_date, end_date)
    if df is None or len(df) < 60:
        return pd.DataFrame()
    return build_features(df)
