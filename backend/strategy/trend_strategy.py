# -*- coding: utf-8 -*-
"""
趋势机构策略（稳定收益）：机构资金趋势，MA20 > MA60 做多。
"""
from __future__ import annotations
from typing import Any
import pandas as pd


class TrendInstitutionStrategy:
    """趋势机构：均线多头排列。"""

    def __init__(self, short_window: int = 20, long_window: int = 60):
        self.short_window = short_window
        self.long_window = long_window

    def generate_signal(self, df: pd.DataFrame) -> int:
        """最后一根 K 线 MA20 > MA60 返回 1，否则 0。"""
        if df is None or len(df) < self.long_window:
            return 0
        ma20 = df["close"].rolling(self.short_window).mean()
        ma60 = df["close"].rolling(self.long_window).mean()
        if ma20.iloc[-1] > ma60.iloc[-1]:
            return 1
        return 0

    def run(self, df: pd.DataFrame) -> dict[str, Any]:
        """返回信号与元数据。"""
        sig = self.generate_signal(df)
        return {"signal": sig, "strategy": "trend_institution"}
