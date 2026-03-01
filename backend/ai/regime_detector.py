# -*- coding: utf-8 -*-
"""
生产级市场状态检测：指数 MA20/MA60 判断 bull / bear。
"""
from __future__ import annotations
import pandas as pd


class RegimeDetector:
    """基于指数日线均线判断牛熊。"""

    def __init__(self, short_window: int = 20, long_window: int = 60):
        self.short_window = short_window
        self.long_window = long_window

    def detect(self, index_df: pd.DataFrame) -> str:
        """
        index_df: 指数 K 线，需含 close。
        返回: "bull" | "bear"
        """
        if index_df is None or len(index_df) < self.long_window:
            return "bear"
        close = index_df["close"] if "close" in index_df.columns else index_df.get("收盘", index_df.iloc[:, 3])
        ma20 = close.rolling(self.short_window).mean()
        ma60 = close.rolling(self.long_window).mean()
        if ma20.iloc[-1] > ma60.iloc[-1]:
            return "bull"
        return "bear"
