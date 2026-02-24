# -*- coding: utf-8 -*-
"""
自动交易系统核心模块：信号引擎、风险控制、仓位管理、订单执行、券商接口、交易主引擎。
"""
from .signal_engine import generate_signals
from .risk_manager import RiskManager, check_risk
from .position_manager import calculate_position
from .order_executor import OrderExecutor
from .broker_interface import Broker
from .trading_engine import TradingEngine, run_daily_trading

__all__ = [
    "generate_signals",
    "RiskManager",
    "check_risk",
    "calculate_position",
    "OrderExecutor",
    "Broker",
    "TradingEngine",
    "run_daily_trading",
]
