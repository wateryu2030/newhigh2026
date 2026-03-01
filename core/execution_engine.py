# -*- coding: utf-8 -*-
"""
ExecutionEngine：接收订单请求，委托 Broker 执行，可选记录与风控前置。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .broker import BrokerProtocol
from .order import Order, OrderStatus


class ExecutionEngine:
    """
    执行引擎：submit_order / cancel_order 委托给 Broker；
    可扩展：下单前风控、日志、通知。
    """

    def __init__(self, broker: BrokerProtocol):
        self.broker = broker
        self._order_log: List[Dict[str, Any]] = []

    def submit_order(
        self,
        symbol: str,
        qty: float,
        side: str = "BUY",
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        """
        提交订单。返回 Broker 返回的订单信息（含 order_id, status 等）；失败返回 None。
        """
        if not getattr(self.broker, "_connected", False):
            self.broker.connect()
        out = self.broker.send_order(
            symbol=symbol,
            qty=qty,
            side=side.upper(),
            price=price,
            order_type=order_type or "limit",
        )
        if out:
            self._order_log.append(out)
        return out

    def cancel_order(self, order_id: str) -> bool:
        return self.broker.cancel_order(order_id)

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """从本地日志查找订单；若 Broker 有 get_order 可委托。"""
        for o in reversed(self._order_log):
            if o.get("order_id") == order_id:
                return o
        if hasattr(self.broker, "_orders") and order_id in getattr(self.broker, "_orders", {}):
            return self.broker._orders[order_id]
        return None

    def list_orders(self, symbol: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Dict[str, Any]]:
        """列出已记录订单，可按 symbol、status 过滤。"""
        out = list(self._order_log)
        if symbol:
            out = [o for o in out if o.get("symbol") == symbol]
        if status is not None:
            out = [o for o in out if o.get("status") == status.value]
        return out
