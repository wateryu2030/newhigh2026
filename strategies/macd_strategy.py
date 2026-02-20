# -*- coding: utf-8 -*-
"""MACD 金叉死叉策略。"""
from typing import List, Dict, Any
import pandas as pd
from .base import BaseStrategy


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    dif = ema_fast - ema_slow
    dea = _ema(dif, signal)
    macd = (dif - dea) * 2
    return dif, dea, macd


class MACDStrategy(BaseStrategy):
    name = "MACD"
    description = "MACD 金叉买入、死叉卖出"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or len(df) < self.slow + self.signal:
            return []
        df = df.copy()
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        dif, dea, macd = _macd(df["close"], self.fast, self.slow, self.signal)
        df["dif"] = dif
        df["dea"] = dea
        df["macd"] = macd
        df = df.dropna(subset=["dif", "dea", "close"])
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
            if float(row["dif"]) > float(row["dea"]) and float(prev["dif"]) <= float(prev["dea"]):
                signals.append({"date": date_str, "type": "BUY", "price": close, "reason": "MACD 金叉"})
            if float(row["dif"]) < float(row["dea"]) and float(prev["dif"]) >= float(prev["dea"]):
                signals.append({"date": date_str, "type": "SELL", "price": close, "reason": "MACD 死叉"})
        return signals
