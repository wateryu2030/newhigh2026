# -*- coding: utf-8 -*-
"""
AI 基金经理系统（Portfolio Brain）：策略注册、风险预算、资金分配、市场状态、再平衡与执行。
"""
from .manager_engine import FundManager
from .strategy_layer.strategy_registry import StrategyRegistry
from .strategy_layer.strategy_metrics import StrategyMetrics
from .capital_layer.risk_budget import RiskBudget
from .capital_layer.position_optimizer import PositionOptimizer
from .risk_layer.regime_detector import RegimeDetector
from .risk_layer.portfolio_risk import PortfolioRisk
from .risk_layer.drawdown_control import DrawdownControl
from .ai_layer.ai_allocator import AIAllocator

__all__ = [
    "FundManager",
    "StrategyRegistry",
    "StrategyMetrics",
    "RiskBudget",
    "PositionOptimizer",
    "RegimeDetector",
    "PortfolioRisk",
    "DrawdownControl",
    "AIAllocator",
]
