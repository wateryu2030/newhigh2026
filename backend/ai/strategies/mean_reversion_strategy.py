# -*- coding: utf-8 -*-
"""
均值回归策略：价格偏离均线过远时反向信号（超卖买、超买卖）。
"""
from __future__ import annotations
from typing import Any, Dict, List

import pandas as pd

from .base_strategy import BaseStrategy


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / (avg_loss + 1e-10)
    return (100 - (100 / (1 + rs))).fillna(50)


class MeanReversionStrategy(BaseStrategy):
    name = "均值回归"
    strategy_id = "mean_reversion"

    def generate_signals(self, data: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            items = list(data.items())
        else:
            return out
        for symbol, df in items:
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 25:
                continue
            try:
                close = df["close"].astype(float)
                ma20 = close.rolling(20, min_periods=1).mean()
                rsi = _rsi(close, 14)
                last_rsi = rsi.iloc[-1]
                last_close = close.iloc[-1]
                last_ma = ma20.iloc[-1]
                dev = (last_close - last_ma) / (last_ma + 1e-10)
                if last_rsi < 30 or dev < -0.08:
                    out.append({"symbol": symbol, "signal": "buy", "confidence": min(0.9, 0.5 + (30 - last_rsi) / 100)})
                elif last_rsi > 70 or dev > 0.08:
                    out.append({"symbol": symbol, "signal": "sell", "confidence": min(0.9, 0.5 + (last_rsi - 70) / 100)})
                else:
                    out.append({"symbol": symbol, "signal": "hold", "confidence": 0.5})
            except Exception:
                continue
        return out
