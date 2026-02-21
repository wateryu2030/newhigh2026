# -*- coding: utf-8 -*-
"""KDJ 指标策略。K、D、J 金叉/超卖买入、死叉/超买卖出。"""
from typing import List, Dict, Any
import pandas as pd
from .base import BaseStrategy


def _kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9, m1: int = 3, m2: int = 3):
    """KDJ 计算。RSV = (C-L9)/(H9-L9)*100, K = SMA(RSV,m1), D = SMA(K,m2), J = 3K-2D"""
    low_n = low.rolling(n, min_periods=1).min()
    high_n = high.rolling(n, min_periods=1).max()
    rsv = 100 * (close - low_n) / (high_n - low_n + 1e-10)
    k = rsv.ewm(com=m1 - 1, adjust=False).mean()
    d = k.ewm(com=m2 - 1, adjust=False).mean()
    j = 3 * k - 2 * d
    return k, d, j


class KDJStrategy(BaseStrategy):
    name = "KDJ"
    description = "KDJ 金叉买入、死叉/超买卖出"

    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3, oversold: float = 20, overbought: float = 80):
        self.n = n
        self.m1 = m1
        self.m2 = m2
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or len(df) < self.n + self.m1 + self.m2:
            return []
        df = df.copy()
        if "date" not in df.columns and df.index is not None:
            df["date"] = df.index.astype(str).str[:10]
        k, d, j = _kdj(df["high"], df["low"], df["close"], self.n, self.m1, self.m2)
        df["k"] = k
        df["d"] = d
        df["j"] = j
        df = df.dropna(subset=["k", "d", "j", "close"])
        if len(df) < 2:
            return []
        signals: List[Dict[str, Any]] = []
        for i in range(1, len(df)):
            row = df.iloc[i]
            prev = df.iloc[i - 1]
            date_str = str(row.get("date", df.index[i]))[:10]
            close = float(row["close"])
            k_val = float(row["k"])
            d_val = float(row["d"])
            j_val = float(row["j"])
            if close != close:
                continue
            # 金叉：K 上穿 D，或 J 从超卖区上穿（脱离超卖）
            if k_val > d_val and float(prev["k"]) <= float(prev["d"]):
                signals.append({"date": date_str, "type": "BUY", "price": close, "reason": "KDJ 金叉"})
            elif float(prev["j"]) < self.oversold and j_val >= self.oversold:
                signals.append({"date": date_str, "type": "BUY", "price": close, "reason": "KDJ 超卖回升"})
            # 死叉：K 下穿 D，或 J 从超买区下穿（脱离超买）
            if k_val < d_val and float(prev["k"]) >= float(prev["d"]):
                signals.append({"date": date_str, "type": "SELL", "price": close, "reason": "KDJ 死叉"})
            elif float(prev["j"]) > self.overbought and j_val <= self.overbought:
                signals.append({"date": date_str, "type": "SELL", "price": close, "reason": "KDJ 超买回落"})
        return signals
