# -*- coding: utf-8 -*-
"""
市场状态识别：基于波动率、均线趋势、成交量判断 bull / bear / sideways / high_volatility。
"""
from __future__ import annotations
from typing import Literal

import numpy as np
import pandas as pd

RegimeType = Literal["bull", "bear", "sideways", "high_volatility"]


def detect_regime(df: pd.DataFrame) -> RegimeType:
    """
    根据近期日线判断市场状态。
    df: 至少含 close, volume，建议 60 行以上；可为单标的或指数。
    """
    if df is None or len(df) < 20:
        return "sideways"
    close = df["close"].astype(float)
    ret = close.pct_change().dropna()
    vol_series = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1.0, index=df.index)
    lookback = min(20, len(close) - 1)
    volatility = ret.tail(lookback).std()
    volatility = volatility if pd.notna(volatility) and volatility > 0 else 1e-6
    trend = (close.iloc[-1] / close.iloc[-lookback] - 1.0) if lookback else 0.0
    vol_ma = vol_series.rolling(20, min_periods=1).mean()
    vol_ratio = (vol_series.iloc[-1] / vol_ma.iloc[-1]) if len(vol_ma) and vol_ma.iloc[-1] > 0 else 1.0
    high_vol_threshold = 0.02
    if volatility >= high_vol_threshold:
        return "high_volatility"
    if trend >= 0.03:
        return "bull"
    if trend <= -0.03:
        return "bear"
    return "sideways"


def get_regime_weight(regime: RegimeType) -> float:
    """根据市场状态返回建议仓位系数 (0~1)。"""
    return {"bull": 1.0, "bear": 0.3, "sideways": 0.7, "high_volatility": 0.5}.get(regime, 0.7)
