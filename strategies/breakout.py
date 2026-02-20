# -*- coding: utf-8 -*-
"""突破策略：上破 N 日高点买入，下破 N 日低点卖出。"""
from typing import List, Dict, Any
import pandas as pd
from .base import BaseStrategy


class BreakoutStrategy(BaseStrategy):
    name = "Breakout突破"
    description = "突破 N 日高点买、跌破 N 日低点卖"

    def __init__(self, period: int = 20):
        self.period = period

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or len(df) < self.period + 1:
            return []
        df = df.copy()
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        df["high_n"] = df["high"].rolling(self.period, min_periods=self.period).max()
        df["low_n"] = df["low"].rolling(self.period, min_periods=self.period).min()
        df = df.dropna(subset=["high_n", "low_n", "close"])
        if len(df) < 2:
            return []
        signals: List[Dict[str, Any]] = []
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            date_str = str(row.get("date", df.index[i]))[:10]
            close = float(row["close"])
            high_n = float(row["high_n"])
            low_n = float(row["low_n"])
            if close != close:
                continue
            if float(prev["close"]) <= float(prev["high_n"]) and close > high_n:
                signals.append({"date": date_str, "type": "BUY", "price": close, "reason": f"突破{self.period}日高点"})
            if float(prev["close"]) >= float(prev["low_n"]) and close < low_n:
                signals.append({"date": date_str, "type": "SELL", "price": close, "reason": f"跌破{self.period}日低点"})
        return signals
