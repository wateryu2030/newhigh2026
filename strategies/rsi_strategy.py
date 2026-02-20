# -*- coding: utf-8 -*-
"""RSI 超买超卖策略。"""
from typing import List, Dict, Any
import pandas as pd
from .base import BaseStrategy


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


class RSIStrategy(BaseStrategy):
    name = "RSI"
    description = "RSI 超卖买入、超买卖出"

    def __init__(self, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or len(df) < self.period + 1:
            return []
        df = df.copy()
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        df["rsi"] = _rsi(df["close"], self.period)
        df = df.dropna(subset=["rsi", "close"])
        if len(df) < 2:
            return []
        signals: List[Dict[str, Any]] = []
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            date_str = str(row.get("date", df.index[i]))[:10]
            close = float(row["close"])
            rsi = float(row["rsi"])
            prev_rsi = float(prev["rsi"])
            if rsi != rsi:
                continue
            if prev_rsi <= self.oversold and rsi > self.oversold:
                signals.append({"date": date_str, "type": "BUY", "price": close, "reason": f"RSI 自超卖区回升 (RSI={rsi:.0f})"})
            if prev_rsi >= self.overbought and rsi < self.overbought:
                signals.append({"date": date_str, "type": "SELL", "price": close, "reason": f"RSI 自超买区回落 (RSI={rsi:.0f})"})
        return signals
