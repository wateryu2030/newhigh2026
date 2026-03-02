# -*- coding: utf-8 -*-
"""
订单执行器：机构层统一入口，委托 backend.trading.OrderExecutor。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    from backend.trading.order_executor import OrderExecutor as _OrderExecutor
except ImportError:
    _OrderExecutor = None


class OrderExecutor:
    """订单执行器：place_order / cancel_order / query_order。"""

    def __init__(self, broker: Any = None):
        if _OrderExecutor is None:
            self._impl = None
            return
        if broker is None:
            try:
                from trading.broker_interface import Broker as B
                broker = B("simulation")
            except Exception:
                from backend.trading.broker_interface import Broker as B
                broker = B("simulation")
        self._impl = _OrderExecutor(broker=broker)

    def place_order(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        side: str = "BUY",
    ) -> Optional[Dict[str, Any]]:
        if self._impl is None:
            return {"symbol": symbol, "qty": qty, "side": side, "status": "no_backend"}
        return self._impl.place_order(symbol=symbol, qty=qty, price=price, side=side)

    def cancel_order(self, order_id: Optional[str] = None) -> bool:
        if self._impl is None:
            return False
        return self._impl.cancel_order(order_id=order_id)

    def query_order(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if self._impl is None:
            return []
        return self._impl.query_order(order_id=order_id)
