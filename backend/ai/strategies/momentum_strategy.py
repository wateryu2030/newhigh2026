# -*- coding: utf-8 -*-
"""
动量策略：近期涨幅居前做多、涨幅居后做空/观望。
"""
from __future__ import annotations
from typing import Any, Dict, List

import pandas as pd

from .base_strategy import BaseStrategy


class MomentumStrategy(BaseStrategy):
    name = "动量轮动"
    strategy_id = "momentum"

    def generate_signals(self, data: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not isinstance(data, dict) or len(data) == 0:
            return out
        rets = {}
        for symbol, df in data.items():
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 22:
                continue
            try:
                close = df["close"].astype(float)
                ret_20 = (close.iloc[-1] / close.iloc[-21] - 1.0) if len(close) >= 21 else 0.0
                rets[symbol] = ret_20
            except Exception:
                continue
        if not rets:
            return out
        s = pd.Series(rets)
        q75 = s.quantile(0.75)
        q25 = s.quantile(0.25)
        for symbol, ret in rets.items():
            if ret >= q75:
                out.append({"symbol": symbol, "signal": "buy", "confidence": min(0.95, 0.6 + (ret - q75) * 2)})
            elif ret <= q25:
                out.append({"symbol": symbol, "signal": "sell", "confidence": min(0.8, 0.5 + (q25 - ret) * 2)})
            else:
                out.append({"symbol": symbol, "signal": "hold", "confidence": 0.5})
        return out
