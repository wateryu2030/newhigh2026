# -*- coding: utf-8 -*-
"""
AI 预测特征工程：均线、MACD、RSI、ATR、收益率、波动率、成交量变化等。
"""
from __future__ import annotations
import pandas as pd
import numpy as np


def _ensure_date_column(df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns and df.index is not None:
        df = df.copy()
        df["date"] = df.index.astype(str).str[:10]
    return df


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


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
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    根据日线 OHLCV 构建模型特征。
    要求 df 至少包含 open, high, low, close, volume；可为 index=trade_date 或带 date 列。
    返回带特征列的 DataFrame，含目标前会删除末尾 5 行（无未来收益的样本）。
    """
    if df is None or len(df) < 60:
        return pd.DataFrame()
    df = df.copy()
    if df.index.name == "trade_date" or isinstance(df.index, pd.DatetimeIndex):
        df["date"] = df.index.astype(str).str[:10]
    if "close" not in df.columns:
        return pd.DataFrame()

    close = df["close"].astype(float)
    high = df["high"].astype(float) if "high" in df.columns else close
    low = df["low"].astype(float) if "low" in df.columns else close
    volume = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1.0, index=df.index)

    # 均线
    df["MA5"] = close.rolling(5, min_periods=1).mean()
    df["MA10"] = close.rolling(10, min_periods=1).mean()
    df["MA20"] = close.rolling(20, min_periods=1).mean()
    df["MA60"] = close.rolling(60, min_periods=1).mean()

    # MACD
    macd_line, signal_line, hist = _macd(close)
    df["MACD"] = macd_line
    df["MACD_signal"] = signal_line
    df["MACD_hist"] = hist

    # RSI
    df["RSI"] = _rsi(close, 14)

    # ATR
    df["ATR"] = _atr(high, low, close, 14)

    # 收益率（日）
    df["return_1d"] = close.pct_change(1)
    # 波动率（过去 20 日收益标准差）
    df["volatility_20"] = df["return_1d"].rolling(20, min_periods=2).std().fillna(0)

    # 成交量变化（5 日）
    if "volume" in df.columns and volume is not None and len(volume) > 0:
        df["volume_pct_change_5"] = volume.pct_change(5).fillna(0)
    else:
        df["volume_pct_change_5"] = 0.0

    # 未来 5 日收益（用于训练时构造 target，预测时不用）
    df["forward_return_5d"] = close.shift(-5) / close - 1.0

    df = df.dropna(subset=["MA60", "MACD", "RSI", "ATR", "volatility_20"])
    return df
