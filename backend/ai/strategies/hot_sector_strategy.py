# -*- coding: utf-8 -*-
"""
热点板块策略：成交量与涨幅同时放大视为热点，给出 buy/hold。
"""
from __future__ import annotations
from typing import Any, Dict, List

import pandas as pd

from .base_strategy import BaseStrategy


class HotSectorStrategy(BaseStrategy):
    name = "热点追踪"
    strategy_id = "hot_sector"

    def generate_signals(self, data: Any) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        if not isinstance(data, dict) or len(data) == 0:
            return out
        scores = {}
        for symbol, df in data.items():
            if df is None or not isinstance(df, pd.DataFrame) or len(df) < 21:
                continue
            try:
                close = df["close"].astype(float)
                volume = df["volume"].astype(float) if "volume" in df.columns else pd.Series(1.0, index=df.index)
                ret_5 = (close.iloc[-1] / close.iloc[-6] - 1.0) if len(close) >= 6 else 0.0
                vol_ratio = (volume.iloc[-1] / volume.rolling(20, min_periods=1).mean().iloc[-2]) if len(volume) >= 20 else 1.0
                if vol_ratio < 0.01:
                    vol_ratio = 1.0
                scores[symbol] = ret_5 * min(2.0, vol_ratio)
            except Exception:
                continue
        if not scores:
            return out
        s = pd.Series(scores)
        th = s.quantile(0.7)
        for symbol, sc in scores.items():
            if sc >= th and sc > 0:
                out.append({"symbol": symbol, "signal": "buy", "confidence": min(0.9, 0.5 + sc)})
            else:
                out.append({"symbol": symbol, "signal": "hold", "confidence": 0.5})
        return out
