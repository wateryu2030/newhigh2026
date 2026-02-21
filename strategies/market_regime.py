# -*- coding: utf-8 -*-
"""
市场状态：判断指数趋势 BULL / NEUTRAL / BEAR。
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
import pandas as pd


class MarketRegime(str, Enum):
    BULL = "BULL"
    NEUTRAL = "NEUTRAL"
    BEAR = "BEAR"


class MarketRegimeDetector:
    """
    根据指数 MA20 / MA60 / MA120 判断市场趋势。
    输出：BULL / NEUTRAL / BEAR
    """

    def __init__(self):
        pass

    def detect(self, df: pd.DataFrame) -> MarketRegime:
        """
        :param df: 指数 K 线，至少需 close 列，建议 120 根以上。
        """
        if df is None or len(df) < 60:
            return MarketRegime.NEUTRAL
        d = df.copy()
        d["ma20"] = d["close"].rolling(20, min_periods=1).mean()
        d["ma60"] = d["close"].rolling(60, min_periods=1).mean()
        d["ma120"] = d["close"].rolling(120, min_periods=1).mean()
        row = d.iloc[-1]
        close = float(row["close"])
        ma20 = float(row["ma20"])
        ma60 = float(row["ma60"])
        ma120 = float(row["ma120"])
        if ma20 <= 0 or ma60 <= 0:
            return MarketRegime.NEUTRAL
        if close > ma20 and ma20 > ma60:
            return MarketRegime.BULL
        if close < ma20 and ma20 < ma60:
            return MarketRegime.BEAR
        return MarketRegime.NEUTRAL
