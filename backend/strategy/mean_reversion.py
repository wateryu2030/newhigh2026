# -*- coding: utf-8 -*-
"""
均值回归策略（防震荡）：RSI < 30 买入。
生产级组合权重建议 20%。
"""
from __future__ import annotations
from typing import Any, Dict, List
import pandas as pd


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=1).mean()
    avg_loss = loss.rolling(period, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


class MeanReversion:
    def __init__(self, rsi_period: int = 14, rsi_buy: float = 30.0, rps_sell: float = 70.0):
        self.rsi_period = rsi_period
        self.rsi_buy = rsi_buy
        self.rsi_sell = rps_sell

    def generate(self, df: pd.DataFrame, code: str = "") -> List[Dict[str, Any]]:
        """RSI < 30 返回 buy。"""
        if df is None or len(df) < self.rsi_period + 1:
            return []
        close = df["close"] if "close" in df.columns else df.get("收盘", df.iloc[:, 3])
        rsi = _compute_rsi(close, self.rsi_period)
        if rsi.iloc[-1] < self.rsi_buy:
            return [{"symbol": code or getattr(df, "code", ""), "action": "buy"}]
        return []
