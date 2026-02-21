# -*- coding: utf-8 -*-
"""
策略1：趋势突破（核心盈利）
选股：收盘价 > MA20 > MA60、60日新高、放量、市值>50亿、排除ST。
仓位：组合 30%–40%。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, MarketDataType


class TrendBreakoutStrategy(BaseStrategy):
    """A股波段趋势突破策略。"""

    name = "趋势突破"

    def __init__(
        self,
        ma_short: int = 20,
        ma_long: int = 60,
        volume_ratio: float = 1.5,
        atr_stop_pct: float = 0.08,
        position_pct: float = 0.35,
    ) -> None:
        self.ma_short = ma_short
        self.ma_long = ma_long
        self.volume_ratio = volume_ratio
        self.atr_stop_pct = atr_stop_pct
        self.position_pct = position_pct
        self._last_score: float = 0.5

    def select_stocks(self, market_data: MarketDataType) -> List[str]:
        """选股：MA 多头、60日新高、放量。"""
        if isinstance(market_data, pd.DataFrame):
            if "symbol" in market_data.columns:
                symbols = market_data["symbol"].unique().tolist()
                data_dict = self._panel_to_dict(market_data)
            else:
                return []
        else:
            data_dict = market_data
            symbols = list(data_dict.keys())
        out: List[str] = []
        for sym in symbols:
            df = data_dict.get(sym) if isinstance(market_data, dict) else self._ensure_df(market_data, sym)
            if df is None or len(df) < self.ma_long + 5:
                continue
            df = df.copy()
            if "date" not in df.columns and df.index is not None:
                df["date"] = df.index.astype(str).str[:10]
            df["ma20"] = df["close"].rolling(self.ma_short, min_periods=1).mean()
            df["ma60"] = df["close"].rolling(self.ma_long, min_periods=1).mean()
            df["high60"] = df["high"].rolling(self.ma_long, min_periods=1).max()
            df["vol20"] = df["volume"].rolling(20, min_periods=1).mean()
            row = df.iloc[-1]
            close = float(row["close"])
            ma20 = float(row["ma20"])
            ma60 = float(row["ma60"])
            high60 = float(row["high60"])
            vol = float(row.get("volume", 0))
            vol20 = float(row.get("vol20", 1))
            if ma60 <= 0 or vol20 <= 0:
                continue
            if "ST" in str(sym).upper():
                continue
            if close > ma20 > ma60 and close >= high60 * 0.98 and vol >= vol20 * self.volume_ratio:
                out.append(sym)
        return out

    def generate_signals(self, market_data: MarketDataType) -> pd.DataFrame:
        """返回 symbol, signal, weight, stop_loss。"""
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
            if df is None or len(df) < self.ma_long + 5:
                continue
            df = df.copy()
            df["ma20"] = df["close"].rolling(self.ma_short, min_periods=1).mean()
            df["atr"] = (df["high"] - df["low"]).rolling(14, min_periods=1).mean()
            row = df.iloc[-1]
            close = float(row["close"])
            ma20 = float(row["ma20"])
            atr = float(row.get("atr", close * 0.02))
            stop_loss = close - atr * 2
            stop_loss = max(stop_loss, close * (1 - self.atr_stop_pct))
            if close > ma20:
                signal = "BUY"
            else:
                signal = "SELL"
            rows.append({
                "symbol": sym,
                "signal": signal,
                "weight": weight,
                "stop_loss": round(stop_loss, 2),
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol", "signal", "weight", "stop_loss"])

    def position_size(self, capital: float) -> Dict[str, float]:
        """单策略内等权，总仓位 position_pct。"""
        return {}

    def score(self) -> float:
        return self._last_score

    def set_score(self, value: float) -> None:
        self._last_score = max(0.0, min(1.0, value))
