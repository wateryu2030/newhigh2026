# -*- coding: utf-8 -*-
"""
模拟券商适配器：对接 backend.trading.broker_interface.Broker（模拟模式）。
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from .base import BrokerBase

try:
    from backend.trading.broker_interface import Broker
except Exception:
    Broker = None  # type: ignore


class SimBrokerAdapter(BrokerBase):
    """用现有 Broker(mode='simulation') 实现 BrokerBase。"""

    def __init__(self, initial_cash: float = 1000000.0):
        self._broker: Optional[Any] = None
        self._initial_cash = initial_cash

    def _get_broker(self):
        if self._broker is None and Broker is not None:
            self._broker = Broker(mode="simulation")
            self._broker.connect()
        return self._broker

    def buy(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        b = self._get_broker()
        if b is None:
            return {"symbol": symbol, "qty": int(qty), "side": "BUY", "status": "pending"}
        return b.buy(symbol, qty, price, order_type)

    def sell(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        b = self._get_broker()
        if b is None:
            return {"symbol": symbol, "qty": int(qty), "side": "SELL", "status": "pending"}
        return b.sell(symbol, qty, price, order_type)

    def cancel_order(self, order_id: str) -> bool:
        b = self._get_broker()
        if b is None:
            return False
        return b.cancel_order(order_id)

    def query_position(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        b = self._get_broker()
        if b is None:
            return {}
        return b.query_position(symbol)

    def get_balance(self) -> Dict[str, float]:
        b = self._get_broker()
        if b is None:
            return {"total_asset": self._initial_cash, "cash": self._initial_cash, "frozen": 0.0}
        if hasattr(b, "get_balance"):
            return b.get_balance()
        return {"total_asset": self._initial_cash, "cash": self._initial_cash, "frozen": 0.0}

    def send_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生产级：统一 send_order(order)。"""
        symbol = order.get("symbol") or order.get("code")
        qty = abs(int(order.get("qty", 0) or 0))
        side = (order.get("side") or "BUY").upper()
        price = order.get("price")
        if not symbol or qty <= 0:
            return None
        if side == "BUY":
            return self.buy(symbol, qty, price)
        return self.sell(symbol, qty, price)
