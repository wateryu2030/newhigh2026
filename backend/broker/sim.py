# -*- coding: utf-8 -*-
"""
生产级模拟券商：SimBroker.send_order(order) 可对接 TradingEngine。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from .base import BrokerBase

try:
    from backend.trading.broker_interface import Broker
except Exception:
    Broker = None  # type: ignore

logger = logging.getLogger(__name__)


class SimBroker(BrokerBase):
    """模拟券商：send_order 执行模拟成交并打印。"""

    def __init__(self, initial_cash: float = 1000000.0):
        self._broker: Optional[Any] = None
        self._initial_cash = initial_cash

    def _get_broker(self):
        if self._broker is None and Broker is not None:
            self._broker = Broker(mode="simulation")
            self._broker.connect()
        return self._broker

    def send_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生产级：Sim trade 并打印。"""
        symbol = order.get("symbol") or order.get("code")
        qty = abs(int(order.get("qty", 0) or 0))
        side = (order.get("side") or "BUY").upper()
        price = order.get("price")
        if not symbol or qty <= 0:
            return None
        logger.info("Sim trade: %s %s %s @ %s", side, symbol, qty, price)
        b = self._get_broker()
        if b is None:
            return {"symbol": symbol, "qty": qty, "side": side, "status": "FILLED"}
        if side == "BUY":
            out = b.buy(symbol, qty, price, "limit")
        else:
            out = b.sell(symbol, qty, price, "limit")
        return out

    def buy(self, symbol: str, qty: float, price: Optional[float] = None, order_type: str = "limit") -> Optional[Dict[str, Any]]:
        b = self._get_broker()
        if b is None:
            return {"symbol": symbol, "qty": int(qty), "side": "BUY", "status": "FILLED"}
        return b.buy(symbol, qty, price, order_type)

    def sell(self, symbol: str, qty: float, price: Optional[float] = None, order_type: str = "limit") -> Optional[Dict[str, Any]]:
        b = self._get_broker()
        if b is None:
            return {"symbol": symbol, "qty": int(qty), "side": "SELL", "status": "FILLED"}
        return b.sell(symbol, qty, price, order_type)

    def cancel_order(self, order_id: str) -> bool:
        b = self._get_broker()
        return b.cancel_order(order_id) if b else False

    def query_position(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        b = self._get_broker()
        return b.query_position(symbol) if b else {}

    def get_balance(self) -> Dict[str, float]:
        b = self._get_broker()
        if b and hasattr(b, "get_balance"):
            return b.get_balance()
        return {"total_asset": self._initial_cash, "cash": self._initial_cash, "frozen": 0.0}
