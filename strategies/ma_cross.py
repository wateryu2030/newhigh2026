# -*- coding: utf-8 -*-
"""均线金叉/死叉策略。"""
from typing import List, Dict, Any
import pandas as pd
from .base import BaseStrategy


class MACrossStrategy(BaseStrategy):
    name = "MA均线"
    description = "MA5 上穿/下穿 MA20 金叉死叉"

    def __init__(self, fast: int = 5, slow: int = 20):
        self.fast = fast
        self.slow = slow

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or len(df) < max(self.fast, self.slow) + 1:
            return []
        df = df.copy()
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        df["ma_fast"] = df["close"].rolling(self.fast, min_periods=1).mean()
        df["ma_slow"] = df["close"].rolling(self.slow, min_periods=1).mean()
        df = df.dropna(subset=["ma_fast", "ma_slow", "close"])
        if len(df) < 2:
            return []
        signals: List[Dict[str, Any]] = []
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            date_str = str(row.get("date", df.index[i]))[:10]
            close = float(row["close"])
            if close != close:
                continue
            cross_up = (float(row["ma_fast"]) > float(row["ma_slow"]) and
                       float(prev["ma_fast"]) <= float(prev["ma_slow"]))
            if cross_up:
                signals.append({"date": date_str, "type": "BUY", "price": close, "reason": "MA%d 上穿 MA%d（金叉）" % (self.fast, self.slow)})
            cross_down = (float(row["ma_fast"]) < float(row["ma_slow"]) and
                         float(prev["ma_fast"]) >= float(prev["ma_slow"]))
            if cross_down:
                signals.append({"date": date_str, "type": "SELL", "price": close, "reason": "MA%d 下穿 MA%d（死叉）" % (self.fast, self.slow)})
        return signals
