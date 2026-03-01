# -*- coding: utf-8 -*-
"""
机构趋势策略（稳定器）：MA20 > MA60 做多。
生产级组合权重建议 30%。
"""
from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd


class TrendStrategy:
    def __init__(self, short_window: int = 20, long_window: int = 60):
        self.short_window = short_window
        self.long_window = long_window

    def generate(self, df: pd.DataFrame, code: str = "") -> List[Dict[str, Any]]:
        """返回 [{"symbol": code, "action": "buy"}] 或 []。"""
        if df is None or len(df) < self.long_window:
            return []
        close = df["close"] if "close" in df.columns else df.get("收盘", df.iloc[:, 3])
        ma20 = close.rolling(self.short_window).mean()
        ma60 = close.rolling(self.long_window).mean()
        if ma20.iloc[-1] > ma60.iloc[-1]:
            return [{"symbol": code or getattr(df, "code", ""), "action": "buy"}]
        return []


TrendInstitutionStrategy = TrendStrategy
