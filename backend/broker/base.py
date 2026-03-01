# -*- coding: utf-8 -*-
"""
券商抽象接口：buy / sell / cancel / query_position / get_balance。
实盘可接 QMT、同花顺、聚宽、掘金等。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BrokerBase(ABC):
    """券商适配层抽象基类。"""

    @abstractmethod
    def buy(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def sell(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    def query_position(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """返回 { order_book_id: { qty, cost, ... } }"""
        pass

    def get_balance(self) -> Dict[str, float]:
        """返回 { total_asset, cash, frozen } 等。"""
        return {"total_asset": 0.0, "cash": 0.0, "frozen": 0.0}

    def send_order(self, order: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        生产级统一入口：order 含 symbol, qty, side (BUY|SELL), price 等。
        默认实现根据 side 调 buy/sell。
        """
        symbol = order.get("symbol") or order.get("code")
        qty = abs(int(order.get("qty", 0) or 0))
        side = (order.get("side") or "BUY").upper()
        price = order.get("price")
        if not symbol or qty <= 0:
            return None
        if side == "BUY":
            return self.buy(symbol, qty, price)
        return self.sell(symbol, qty, price)
