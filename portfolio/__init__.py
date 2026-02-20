# -*- coding: utf-8 -*-
"""
多策略组合投资组合系统。
按权重合并多个策略的净值曲线与信号，输出统一回测结果结构。
"""
from .portfolio import (
    run_portfolio_backtest,
    aggregate_curves,
)
from .portfolio_engine import PortfolioEngine

__all__ = [
    "run_portfolio_backtest",
    "aggregate_curves",
    "PortfolioEngine",
]
