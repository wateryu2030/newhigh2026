# -*- coding: utf-8 -*-
"""
市场环境识别：BULL / NEUTRAL / BEAR，用于策略权重动态调整。
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, Optional, Tuple
import pandas as pd


class MarketRegime(str, Enum):
    BULL = "BULL"
    NEUTRAL = "NEUTRAL"
    BEAR = "BEAR"


# 各市场状态下策略权重（趋势突破, 强势回调, ETF轮动）
REGIME_WEIGHTS: Dict[MarketRegime, Tuple[float, float, float]] = {
    MarketRegime.BULL: (0.40, 0.30, 0.10),
    MarketRegime.NEUTRAL: (0.30, 0.25, 0.20),
    MarketRegime.BEAR: (0.20, 0.10, 0.40),
}


class MarketRegimeDetector:
    """
    基于上证/沪深300指数与 MA20/MA60 判断市场状态。
    """

    def __init__(self, ma_short: int = 20, ma_long: int = 60) -> None:
        self.ma_short = ma_short
        self.ma_long = ma_long

    def detect(self, index_df: pd.DataFrame) -> MarketRegime:
        """
        :param index_df: 指数 K 线，含 close，建议 60 根以上。
        if index > MA60: BULL
        elif index > MA20: NEUTRAL
        else: BEAR
        """
        if index_df is None or len(index_df) < self.ma_long:
            return MarketRegime.NEUTRAL
        df = index_df.copy()
        if "close" not in df.columns:
            return MarketRegime.NEUTRAL
        df["ma20"] = df["close"].rolling(self.ma_short, min_periods=1).mean()
        df["ma60"] = df["close"].rolling(self.ma_long, min_periods=1).mean()
        row = df.iloc[-1]
        close = float(row["close"])
        ma20 = float(row["ma20"])
        ma60 = float(row["ma60"])
        if ma60 <= 0:
            return MarketRegime.NEUTRAL
        if close > ma60:
            return MarketRegime.BULL
        if close > ma20:
            return MarketRegime.NEUTRAL
        return MarketRegime.BEAR

    def get_strategy_weights(self, regime: MarketRegime) -> Tuple[float, float, float]:
        """返回 (趋势突破权重, 强势回调权重, ETF轮动权重)。"""
        return REGIME_WEIGHTS.get(regime, (0.30, 0.25, 0.20))
