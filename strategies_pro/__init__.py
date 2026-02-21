# -*- coding: utf-8 -*-
"""
A股机构级策略模块 strategies_pro

包含：趋势突破、强势回调、ETF轮动、市场环境识别、策略评分与动态权重。
与现有组合管理、交易模块兼容，不破坏原有代码结构。
"""
from .base_strategy import BaseStrategy
from .trend_breakout import TrendBreakoutStrategy
from .strong_pullback import StrongPullbackStrategy
from .etf_rotation import ETFRotationStrategy
from .market_regime import MarketRegime, MarketRegimeDetector
from .strategy_scorer import StrategyScorer
from .strategy_manager import StrategyManager

__all__ = [
    "BaseStrategy",
    "TrendBreakoutStrategy",
    "StrongPullbackStrategy",
    "ETFRotationStrategy",
    "MarketRegime",
    "MarketRegimeDetector",
    "StrategyScorer",
    "StrategyManager",
]
