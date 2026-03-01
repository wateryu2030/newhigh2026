# -*- coding: utf-8 -*-
"""
龙头策略（高收益核心）：收盘 > 60 日高、放量、RPS>90。
生产级组合权重建议 40%。
"""
from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd


class DragonStrategy:
    def __init__(self, high_window: int = 60, volume_ma_window: int = 20, volume_ratio: float = 2.0, rps_min: float = 90.0):
        self.high_window = high_window
        self.volume_ma_window = volume_ma_window
        self.volume_ratio = volume_ratio
        self.rps_min = rps_min

    def generate(self, df: pd.DataFrame, code: str = "") -> List[Dict[str, Any]]:
        """返回 [{"symbol": code, "action": "buy"}] 或 []。"""
        if df is None or len(df) < max(self.high_window, self.volume_ma_window):
            return []
        d = df.copy()
        if "high" not in d.columns and "最高" in d.columns:
            d["high"] = d["最高"]
        if "close" not in d.columns and "收盘" in d.columns:
            d["close"] = d["收盘"]
        if "volume" not in d.columns and "成交量" in d.columns:
            d["volume"] = d["成交量"]
        d["high_60"] = d["high"].rolling(self.high_window).max()
        d["volume_ma20"] = d["volume"].rolling(self.volume_ma_window).mean()
        if "rps" not in d.columns:
            d["rps"] = 50.0
        row = d.iloc[-1]
        cond1 = row["close"] > row["high_60"]
        cond2 = row["volume"] > row["volume_ma20"] * self.volume_ratio
        cond3 = row["rps"] > self.rps_min
        if cond1 and cond2 and cond3:
            return [{"symbol": code or getattr(df, "code", ""), "action": "buy"}]
        return []


# 兼容旧名
DragonLeaderStrategy = DragonStrategy
