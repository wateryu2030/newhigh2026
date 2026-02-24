# -*- coding: utf-8 -*-
"""
趋势突破策略：均线多头排列、价格突破近期高点 → buy；反之 sell/hold。
"""
from __future__ import annotations
from typing import Any, Dict, List

import pandas as pd

from .base_strategy import BaseStrategy


class TrendStrategy(BaseStrategy):
    name = "趋势突破"
    strategy_id = "trend"

    def generate_signals(self, data: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if isinstance(data, dict):
            items = list(data.items())
        else:
            return out
        for symbol, df in items:
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 30:
                continue
            try:
                close = df["close"].astype(float)
                ma5 = close.rolling(5, min_periods=1).mean()
                ma20 = close.rolling(20, min_periods=1).mean()
                ma60 = close.rolling(60, min_periods=1).mean()
                high_20 = close.rolling(20, min_periods=1).max()
                last = close.iloc[-1]
                if ma5.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1] and last >= high_20.iloc[-2]:
                    out.append({"symbol": symbol, "signal": "buy", "confidence": 0.75})
                elif ma5.iloc[-1] < ma20.iloc[-1]:
                    out.append({"symbol": symbol, "signal": "sell", "confidence": 0.6})
                else:
                    out.append({"symbol": symbol, "signal": "hold", "confidence": 0.5})
            except Exception:
                continue
        return out
