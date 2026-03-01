# -*- coding: utf-8 -*-
"""
Broker 抽象与 SimBroker：统一券商接口，模拟盘实现订单状态机与资金/持仓更新。
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Protocol

from .order import Order, OrderStatus


class BrokerProtocol(Protocol):
    """券商接口协议：connect、资金、持仓、下单、撤单。"""

    def connect(self) -> bool:
        ...

    def get_balance(self) -> Dict[str, Any]:
        ...

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        ...

    def send_order(
        self,
        symbol: str,
        qty: float,
        side: str = "BUY",
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        ...

    def cancel_order(self, order_id: str) -> bool:
        ...


class SimBroker:
    """
    模拟券商：订单状态机 submitted -> filled（立即成交）或 cancelled；
    成交后更新资金与持仓，支持市价/限价。
    """

    def __init__(
        self,
        initial_cash: float = 1_000_000.0,
        slippage_pct: float = 0.0,
        commission_pct: float = 0.0003,
    ):
        self.initial_cash = initial_cash
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self._connected = False
        self._cash = initial_cash
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._order_id = 0

    def connect(self) -> bool:
        self._connected = True
        return True

    def get_balance(self) -> Dict[str, Any]:
        if not self._connected:
            self.connect()
        mv = sum(
            p.get("market_value", p.get("qty", 0) * p.get("avg_price", 0))
            for p in self._positions.values()
        )
        return {
            "cash": self._cash,
            "total_asset": self._cash + mv,
            "frozen": 0.0,
        }

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        if not self._connected:
            self.connect()
        return dict(self._positions)

    def _next_order_id(self) -> str:
        self._order_id += 1
        return f"sim_{self._order_id}"

    def _apply_slippage(self, price: float, side: str) -> float:
        if self.slippage_pct <= 0:
            return price
        if side.upper() == "BUY":
            return price * (1 + self.slippage_pct)
        return price * (1 - self.slippage_pct)

    def send_order(
        self,
        symbol: str,
        qty: float,
        side: str = "BUY",
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        if not self._connected:
            self.connect()
        side = (side or "BUY").upper()
        if side not in ("BUY", "SELL"):
            return None
        qty = int(qty)
        if qty <= 0:
            return None
        # 限价单必须带价格；市价单若未传 price，模拟层无法成交，返回 REJECTED
        if price is None or price <= 0:
            order_id = self._next_order_id()
            order = {
                "order_id": order_id,
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "price": price,
                "order_type": order_type,
                "status": OrderStatus.REJECTED.value,
                "filled_qty": 0,
                "filled_avg_price": None,
            }
            self._orders[order_id] = order
            return order
        fill_price = self._apply_slippage(float(price), side)
        commission = (qty * fill_price) * self.commission_pct
        order_id = self._next_order_id()
        if side == "BUY":
            cost = qty * fill_price + commission
            if self._cash < cost:
                order = {
                    "order_id": order_id,
                    "symbol": symbol,
                    "qty": qty,
                    "side": side,
                    "price": price,
                    "order_type": order_type,
                    "status": OrderStatus.REJECTED.value,
                    "filled_qty": 0,
                    "filled_avg_price": None,
                }
                self._orders[order_id] = order
                return order
            self._cash -= cost
            pos = self._positions.get(symbol, {"qty": 0, "avg_price": 0, "market_value": 0})
            old_qty, old_avg = pos["qty"], pos.get("avg_price", 0)
            new_qty = old_qty + qty
            new_avg = (old_qty * old_avg + qty * fill_price) / new_qty if new_qty else 0
            self._positions[symbol] = {"qty": new_qty, "avg_price": new_avg, "market_value": new_qty * fill_price}
        else:
            pos = self._positions.get(symbol, {"qty": 0})
            hold_qty = pos.get("qty", 0)
            if hold_qty < qty:
                order = {
                    "order_id": order_id,
                    "symbol": symbol,
                    "qty": qty,
                    "side": side,
                    "price": price,
                    "order_type": order_type,
                    "status": OrderStatus.REJECTED.value,
                    "filled_qty": 0,
                    "filled_avg_price": None,
                }
                self._orders[order_id] = order
                return order
            proceed = qty * fill_price - commission
            self._cash += proceed
            new_qty = hold_qty - qty
            if new_qty <= 0:
                self._positions.pop(symbol, None)
            else:
                self._positions[symbol] = {**pos, "qty": new_qty}
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "price": price,
            "order_type": order_type,
            "status": OrderStatus.FILLED.value,
            "filled_qty": qty,
            "filled_avg_price": fill_price,
        }
        self._orders[order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders:
            s = self._orders[order_id].get("status", "")
            if s == OrderStatus.SUBMITTED.value:
                self._orders[order_id]["status"] = OrderStatus.CANCELLED.value
                return True
        return False
