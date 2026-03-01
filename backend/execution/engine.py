# -*- coding: utf-8 -*-
"""
执行引擎：统一入口 place_order / cancel_order，委托 OrderManager 与 BrokerAPI。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    from backend.execution.order_manager import OrderManager
except Exception:
    OrderManager = None  # type: ignore


class ExecutionEngine:
    """下单、撤单、查询；可选滑点等。"""

    def __init__(self, broker_mode: str = "simulation"):
        self._order_manager: Optional[Any] = None
        self._broker_mode = broker_mode

    def _get_order_manager(self):
        if self._order_manager is None and OrderManager is not None:
            from backend.execution.broker_api import BrokerAPI
            self._order_manager = OrderManager(broker=BrokerAPI(mode=self._broker_mode))
        return self._order_manager

    def place_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        price: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """下单。side: BUY | SELL。"""
        om = self._get_order_manager()
        if om is None:
            return {"symbol": symbol, "qty": qty, "side": side, "status": "pending"}
        return om.place_order(symbol, qty, side, price)

    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        om = self._get_order_manager()
        if om is None:
            return False
        return om.cancel_order(order_id)

    def query_orders(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询委托。"""
        om = self._get_order_manager()
        if om is None:
            return []
        return om.query_orders(order_id)
