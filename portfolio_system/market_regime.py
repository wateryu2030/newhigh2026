# -*- coding: utf-8 -*-
"""
市场状态识别：BULL / NEUTRAL / BEAR，用于组合仓位与策略切换。
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
    基于指数 MA20 / MA60 / MA120 的市场状态识别。
    用于组合仓位调节：BULL 满仓、NEUTRAL 半仓、BEAR 轻仓。
    """

    def __init__(self, ma_short: int = 20, ma_mid: int = 60, ma_long: int = 120) -> None:
        self.ma_short = ma_short
        self.ma_mid = ma_mid
        self.ma_long = ma_long

    def detect(self, df: pd.DataFrame) -> MarketRegime:
        """
        :param df: 指数 K 线，需 close 列，建议 120 根以上。
        """
        if df is None or len(df) < self.ma_mid:
            return MarketRegime.NEUTRAL
        d = df.copy()
        if "close" not in d.columns:
            return MarketRegime.NEUTRAL
        d["ma20"] = d["close"].rolling(self.ma_short, min_periods=1).mean()
        d["ma60"] = d["close"].rolling(self.ma_mid, min_periods=1).mean()
        d["ma120"] = d["close"].rolling(self.ma_long, min_periods=1).mean()
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

    def get_position_scale(self, regime: MarketRegime) -> float:
        """根据市场状态返回建议仓位比例 0~1。"""
        if regime == MarketRegime.BULL:
            return 1.0
        if regime == MarketRegime.NEUTRAL:
            return 0.6
        return 0.3
