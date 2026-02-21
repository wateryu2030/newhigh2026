# -*- coding: utf-8 -*-
"""
机构级 A 股组合系统 portfolio_system

目标年化 20~40%，多策略组合、市场状态识别、风控、回测、模拟交易、绩效报告。
面向对象设计，Python 3.11+，类型注解完整，交易信号可接 paper_trading 执行。
"""
from .config import PortfolioConfig, RiskConfig
from .market_regime import MarketRegime, MarketRegimeDetector
from .risk_control import RiskController, RiskLevel
from .strategy_pool import StrategyPool, StrategyWeight
from .portfolio_engine import PortfolioEngine
from .backtester import Backtester
from .simulator import PortfolioSimulator
from .performance import PerformanceReport

__all__ = [
    "PortfolioConfig",
    "RiskConfig",
    "MarketRegime",
    "MarketRegimeDetector",
    "RiskController",
    "RiskLevel",
    "StrategyPool",
    "StrategyWeight",
    "PortfolioEngine",
    "Backtester",
    "PortfolioSimulator",
    "PerformanceReport",
]
