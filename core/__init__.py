# -*- coding: utf-8 -*-
"""核心模块：信号生成、趋势预测、Broker/订单/执行/组合骨架"""

from .signals import generate_signals
from .prediction import predict_trend
from .order import Order, OrderStatus
from .broker import BrokerProtocol, SimBroker
from .portfolio_manager import PortfolioManager
from .execution_engine import ExecutionEngine
from .portfolio_allocator import StrategyWeights, allocate as portfolio_allocate, normalize_weights, CombinedScheduler

__all__ = [
    "generate_signals",
    "predict_trend",
    "Order",
    "OrderStatus",
    "BrokerProtocol",
    "SimBroker",
    "PortfolioManager",
    "ExecutionEngine",
    "StrategyWeights",
    "portfolio_allocate",
    "normalize_weights",
    "CombinedScheduler",
]
