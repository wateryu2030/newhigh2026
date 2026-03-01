# -*- coding: utf-8 -*-
"""
龙头突破策略（主收益）：A 股情绪周期。
条件：收盘 > 60 日最高、放量、RPS > 90。
"""
from __future__ import annotations
from typing import Any, Optional
import pandas as pd


class DragonLeaderStrategy:
    """龙头突破：突破前高 + 放量 + 强势 RPS。"""

    def __init__(self, high_window: int = 60, volume_ma_window: int = 20, volume_ratio: float = 2.0, rps_min: float = 90.0):
        self.high_window = high_window
        self.volume_ma_window = volume_ma_window
        self.volume_ratio = volume_ratio
        self.rps_min = rps_min

    def generate_signal(self, df: pd.DataFrame) -> int:
        """最后一根 K 线满足条件返回 1，否则 0。"""
        if df is None or len(df) < max(self.high_window, self.volume_ma_window):
            return 0
        d = df.copy()
        d["high_60"] = d["high"].rolling(self.high_window).max()
        d["volume_ma20"] = d["volume"].rolling(self.volume_ma_window).mean()
        if "rps" not in d.columns:
            d["rps"] = 50.0  # 无 RPS 时默认中性
        row = d.iloc[-1]
        cond1 = row["close"] > row["high_60"]
        cond2 = row["volume"] > row["volume_ma20"] * self.volume_ratio
        cond3 = row["rps"] > self.rps_min
        if cond1 and cond2 and cond3:
            return 1
        return 0

    def run(self, df: pd.DataFrame) -> dict[str, Any]:
        """返回信号与元数据。"""
        sig = self.generate_signal(df)
        return {"signal": sig, "strategy": "dragon_leader"}
