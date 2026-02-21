# -*- coding: utf-8 -*-
"""
策略3：ETF轮动防御
标的：沪深300ETF、中证500ETF、创业板ETF、红利ETF、黄金ETF。
逻辑：20日动量排名，买动量最高。仓位 10%–20%，降低回撤。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np

from .base_strategy import BaseStrategy, MarketDataType

# 常用 ETF 代码（与 AKShare/数据库一致）
DEFAULT_ETF_UNIVERSE = [
    "510300.XSHG",  # 沪深300ETF
    "510500.XSHG",  # 中证500ETF
    "159915.XSHE",  # 创业板ETF
    "510880.XSHG",  # 红利ETF
    "518880.XSHG",  # 黄金ETF
]


class ETFRotationStrategy(BaseStrategy):
    """ETF 动量轮动防御策略。"""

    name = "ETF轮动"

    def __init__(
        self,
        etf_list: Optional[List[str]] = None,
        momentum_days: int = 20,
        position_pct: float = 0.15,
    ) -> None:
        self.etf_list = etf_list or DEFAULT_ETF_UNIVERSE
        self.momentum_days = momentum_days
        self.position_pct = position_pct
        self._last_score: float = 0.5

    def select_stocks(self, market_data: MarketDataType) -> List[str]:
        """选股：20日动量最高的一只 ETF。"""
        if isinstance(market_data, dict):
            data_dict = {k: v for k, v in market_data.items() if k in self.etf_list or k.replace(".XSHG", "").replace(".XSHE", "") in [e.split(".")[0] for e in self.etf_list]}
        else:
            return []
        if not data_dict:
            return []
        momentum_list: List[tuple] = []
        for sym, df in data_dict.items():
            if df is None or len(df) < self.momentum_days + 1:
                continue
            close_now = float(df["close"].iloc[-1])
            close_old = float(df["close"].iloc[-self.momentum_days - 1])
            if close_old <= 0:
                continue
            ret = (close_now - close_old) / close_old
            momentum_list.append((sym, ret))
        if not momentum_list:
            return []
        momentum_list.sort(key=lambda x: x[1], reverse=True)
        return [momentum_list[0][0]]

    def generate_signals(self, market_data: MarketDataType) -> pd.DataFrame:
        """买入动量最高 ETF，权重 position_pct。"""
        selected = self.select_stocks(market_data)
        rows: List[Dict[str, Any]] = []
        for sym in selected:
            rows.append({
                "symbol": sym,
                "signal": "BUY",
                "weight": self.position_pct,
                "stop_loss": 0.0,
            })
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol", "signal", "weight", "stop_loss"])

    def score(self) -> float:
        return self._last_score

    def set_score(self, value: float) -> None:
        self._last_score = max(0.0, min(1.0, value))
