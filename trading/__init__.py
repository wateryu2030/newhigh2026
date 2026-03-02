# -*- coding: utf-8 -*-
"""
交易层：订单执行与券商接口，机构级组合系统统一入口。
委托 backend.trading 实现。
"""
from __future__ import annotations

try:
    from backend.trading.order_executor import OrderExecutor
    from backend.trading.broker_interface import Broker
except ImportError:
    OrderExecutor = None  # type: ignore
    Broker = None  # type: ignore

__all__ = ["OrderExecutor", "Broker"]
