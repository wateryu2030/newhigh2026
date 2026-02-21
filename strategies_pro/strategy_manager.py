# -*- coding: utf-8 -*-
"""
策略管理器：统一管理所有策略，分配权重，输出组合信号。
与现有组合管理、交易模块兼容。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
import pandas as pd

from .base_strategy import BaseStrategy, MarketDataType
from .market_regime import MarketRegime, MarketRegimeDetector
from .strategy_scorer import StrategyScorer


class StrategyManager:
    """
    统一管理趋势突破、强势回调、ETF轮动等策略。
    输出统一信号：symbol | weight | strategy
    """

    def __init__(
        self,
        strategies: Optional[List[BaseStrategy]] = None,
        regime_detector: Optional[MarketRegimeDetector] = None,
        scorer: Optional[StrategyScorer] = None,
    ) -> None:
        from .trend_breakout import TrendBreakoutStrategy
        from .strong_pullback import StrongPullbackStrategy
        from .etf_rotation import ETFRotationStrategy

        self.strategies = strategies or [
            TrendBreakoutStrategy(position_pct=0.35),
            StrongPullbackStrategy(position_pct=0.25),
            ETFRotationStrategy(position_pct=0.15),
        ]
        self.regime_detector = regime_detector or MarketRegimeDetector()
        self.scorer = scorer or StrategyScorer()
        self._regime_weights: Dict[str, float] = {}
        self._index_df: Optional[pd.DataFrame] = None

    def set_index_data(self, index_df: Optional[pd.DataFrame]) -> None:
        """设置指数数据，用于市场状态识别。"""
        self._index_df = index_df

    def run_all(self, market_data: MarketDataType) -> Dict[str, pd.DataFrame]:
        """运行所有策略，返回 { strategy_name: signals_df }。"""
        regime = MarketRegime.NEUTRAL
        if self._index_df is not None and len(self._index_df) >= 60:
            regime = self.regime_detector.detect(self._index_df)
        tw, sw, ew = self.regime_detector.get_strategy_weights(regime)
        self._regime_weights = {"趋势突破": tw, "强势回调": sw, "ETF轮动": ew}
        out: Dict[str, pd.DataFrame] = {}
        for s in self.strategies:
            df = s.generate_signals(market_data)
            if df is not None and len(df) > 0:
                df = df.copy()
                df["strategy"] = s.name
                out[s.name] = df
        return out

    def allocate_weights(self, strategy_signals: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """按市场状态与策略评分分配各策略权重。"""
        total = 0.0
        weights: Dict[str, float] = {}
        for name, rw in self._regime_weights.items():
            w = rw
            for s in self.strategies:
                if s.name == name:
                    w *= max(0.1, s.score())
                    break
            weights[name] = w
            total += w
        if total > 0:
            for k in weights:
                weights[k] /= total
        return weights

    def get_combined_signals(
        self,
        market_data: MarketDataType,
    ) -> pd.DataFrame:
        """
        获取组合信号。
        :return: DataFrame 列 symbol, weight, strategy（及 signal, stop_loss 等）
        """
        raw = self.run_all(market_data)
        alloc = self.allocate_weights(raw)
        rows: List[Dict[str, Any]] = []
        for name, df in raw.items():
            w_scale = alloc.get(name, 1.0 / len(raw))
            for _, r in df.iterrows():
                sym = r.get("symbol", "")
                wt = float(r.get("weight", 0)) * w_scale
                rows.append({
                    "symbol": sym,
                    "weight": round(wt, 4),
                    "strategy": name,
                    "signal": r.get("signal", "HOLD"),
                    "stop_loss": r.get("stop_loss"),
                })
        return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol", "weight", "strategy"])

    def rebalance(self) -> None:
        """再平衡：可在此更新各策略评分或权重。"""
        pass
