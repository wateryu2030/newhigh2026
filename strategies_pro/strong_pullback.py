# -*- coding: utf-8 -*-
"""
策略2：强势回调（高胜率）
龙头股回调买入：30日涨幅>20%，回调5–15%，缩量，MA20支撑。
仓位：20%–30%。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, MarketDataType


class StrongPullbackStrategy(BaseStrategy):
    """龙头强势回调策略。"""

    name = "强势回调"

    def __init__(
        self,
        lookback: int = 30,
        gain_min: float = 0.20,
        pullback_min: float = 0.05,
        pullback_max: float = 0.15,
        position_pct: float = 0.25,
    ) -> None:
        self.lookback = lookback
        self.gain_min = gain_min
        self.pullback_min = pullback_min
        self.pullback_max = pullback_max
        self.position_pct = position_pct
        self._last_score: float = 0.5

    def select_stocks(self, market_data: MarketDataType) -> List[str]:
        """选股：30日涨幅>20%，回调5–15%，缩量，近MA20。"""
        if isinstance(market_data, pd.DataFrame):
            if "symbol" in market_data.columns:
                data_dict = self._panel_to_dict(market_data)
            else:
                return []
        else:
            data_dict = market_data
        out: List[str] = []
        for sym, df in data_dict.items():
            if df is None or len(df) < self.lookback + 5:
                continue
            df = df.copy()
            if "date" not in df.columns and df.index is not None:
                df["date"] = df.index.astype(str).str[:10]
            df["ma20"] = df["close"].rolling(20, min_periods=1).mean()
            df["vol20"] = df["volume"].rolling(20, min_periods=1).mean()
            if len(df) < self.lookback + 1:
                continue
            close_now = float(df["close"].iloc[-1])
            close_30 = float(df["close"].iloc[-self.lookback - 1])
            high_30 = float(df["high"].iloc[-self.lookback:].max())
            vol_now = float(df["volume"].iloc[-1])
            vol20 = float(df["vol20"].iloc[-1])
            ma20 = float(df["ma20"].iloc[-1])
            if close_30 <= 0 or high_30 <= 0:
                continue
            ret_30 = (close_now - close_30) / close_30
            pullback = (high_30 - close_now) / high_30 if high_30 > 0 else 0
            if ret_30 >= self.gain_min and self.pullback_min <= pullback <= self.pullback_max:
                if vol20 > 0 and vol_now <= vol20 * 1.2:
                    if abs(close_now - ma20) / ma20 <= 0.03:
                        out.append(sym)
        return out

    def generate_signals(self, market_data: MarketDataType) -> pd.DataFrame:
        """返回 symbol, signal, weight, stop_loss（MA20）。"""
        selected = self.select_stocks(market_data)
        if isinstance(market_data, dict):
            data_dict = market_data
        else:
            data_dict = {s: self._ensure_df(market_data, s) for s in selected} if selected else {}
        rows: List[Dict[str, Any]] = []
        n = max(1, len(selected))
        weight = self.position_pct / n
        for sym in selected:
            df = data_dict.get(sym)
            if df is None or len(df) < 25:
                continue
            df = df.copy()
            df["ma20"] = df["close"].rolling(20, min_periods=1).mean()
            row = df.iloc[-1]
            close = float(row["close"])
            ma20 = float(row["ma20"])
            if close >= ma20 * 0.98:
                signal = "BUY"
                stop_loss = ma20 * 0.98
            else:
                signal = "SELL"
                stop_loss = close * 0.95
            rows.append({
                "symbol": sym,
                "signal": signal,
                "weight": weight,
                "stop_loss": round(stop_loss, 2),
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol", "signal", "weight", "stop_loss"])

    def score(self) -> float:
        return self._last_score

    def set_score(self, value: float) -> None:
        self._last_score = max(0.0, min(1.0, value))
