# -*- coding: utf-8 -*-
"""
多策略组合投资组合系统。
按权重合并多个策略的净值曲线与信号，输出统一回测结果结构。
支持：主编排、风险平价/夏普最大化、定期再平衡、策略归因。
"""
from .portfolio import (
    run_portfolio_backtest,
    aggregate_curves,
)
from .portfolio_engine import PortfolioEngine
from .multi_strategy_portfolio import (
    MultiStrategyPortfolio,
    PortfolioConfig,
    StrategyConfig,
)
from .capital_allocator import CapitalAllocator
from .rebalancer import PortfolioRebalancer
from .attribution import StrategyAttribution

__all__ = [
    "run_portfolio_backtest",
    "aggregate_curves",
    "PortfolioEngine",
    "MultiStrategyPortfolio",
    "PortfolioConfig",
    "StrategyConfig",
    "CapitalAllocator",
    "PortfolioRebalancer",
    "StrategyAttribution",
]
