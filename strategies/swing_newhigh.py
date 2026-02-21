# -*- coding: utf-8 -*-
"""
波段策略：新高突破 + 均线趋势 + 成交量确认 + 市场过滤。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd

try:
    from .base import BaseStrategy
    from .market_regime import MarketRegime, MarketRegimeDetector
    from .stock_filter import StockFilter
except ImportError:
    from strategies.base import BaseStrategy
    from strategies.market_regime import MarketRegime, MarketRegimeDetector
    from strategies.stock_filter import StockFilter


class SwingNewHighStrategy(BaseStrategy):
    """
    高级 A 股波段策略。

    买入条件：
    1. 收盘价 > MA60
    2. MA20 > MA60
    3. 接近 60 日新高（>= 97%）
    4. 成交量 > 20 日均量 * 1.2
    5. 市场环境不是 HIGH RISK（BEAR）

    卖出条件：
    1. 跌破 MA20
    2. 或止损 8%
    """

    name = "波段新高"
    description = "新高突破 + 均线趋势 + 成交量确认"

    def __init__(
        self,
        stop_loss_pct: float = 0.08,
        high_ratio: float = 0.97,
        volume_ratio: float = 1.2,
    ):
        self.stop_loss_pct = stop_loss_pct
        self.high_ratio = high_ratio
        self.volume_ratio = volume_ratio
        self.regime_detector = MarketRegimeDetector()
        self.stock_filter = StockFilter()

    def generate_signals(
        self,
        df: pd.DataFrame,
        index_df: Optional[pd.DataFrame] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        根据 K 线生成买卖信号。
        :param df: 个股 K 线
        :param index_df: 指数 K 线（用于市场环境判断）
        """
        if df is None or len(df) < 61:
            return []
        regime = MarketRegime.BEAR
        if index_df is not None and len(index_df) >= 60:
            regime = self.regime_detector.detect(index_df)
        if regime == MarketRegime.BEAR:
            return []
        d = df.copy()
        if "date" not in d.columns and d.index is not None:
            d["date"] = d.index.astype(str).str[:10]
        d["ma20"] = d["close"].rolling(20, min_periods=1).mean()
        d["ma60"] = d["close"].rolling(60, min_periods=1).mean()
        d["vol20"] = d["volume"].rolling(20, min_periods=1).mean()
        d["high60"] = d["high"].rolling(60, min_periods=1).max()
        d = d.dropna(subset=["ma20", "ma60", "vol20", "high60", "close"])
        if len(d) < 2:
            return []
        signals: List[Dict[str, Any]] = []
        for i in range(1, len(d)):
            row = d.iloc[i]
            prev = d.iloc[i - 1]
            date_str = str(row.get("date", d.index[i]))[:10]
            close = float(row["close"])
            ma20 = float(row["ma20"])
            ma60 = float(row["ma60"])
            vol20 = float(row["vol20"])
            high60 = float(row["high60"])
            vol = float(row.get("volume", 0))
            if vol20 <= 0 or high60 <= 0:
                continue
            buy_cond1 = close > ma60 and ma20 > ma60
            buy_cond2 = close >= high60 * self.high_ratio
            buy_cond3 = vol >= vol20 * self.volume_ratio
            if buy_cond1 and buy_cond2 and buy_cond3:
                signals.append({
                    "date": date_str,
                    "type": "BUY",
                    "price": close,
                    "reason": "新高突破+均线多头+放量",
                })
            sell_cond1 = close < ma20
            if sell_cond1:
                signals.append({
                    "date": date_str,
                    "type": "SELL",
                    "price": close,
                    "reason": "跌破 MA20",
                })
        return signals
