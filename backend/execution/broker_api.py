# -*- coding: utf-8 -*-
"""
券商接口：place_order(symbol, qty, side)，先实现模拟交易版本，可扩展真实 API。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional


class BrokerAPI:
    """统一券商接口：模拟模式（默认）与真实模式。"""

    def __init__(self, mode: str = "simulation"):
        self.mode = (mode or "simulation").strip().lower()
        self._connected = False
        self._balance = {"total_asset": 1000000.0, "cash": 1000000.0, "frozen": 0.0}
        self._positions: Dict[str, Dict[str, Any]] = {}
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._order_id = 0

    def connect(self) -> bool:
        if self.mode == "live":
            self._connected = True
            return True
        self._connected = True
        return True

    def get_balance(self) -> Dict[str, float]:
        if not self._connected:
            self.connect()
        return dict(self._balance)

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        if not self._connected:
            self.connect()
        return dict(self._positions)

    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        price: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        下单。side: BUY | SELL。
        模拟模式：直接成交并更新资金/持仓。
        """
        if not self._connected:
            self.connect()
        side = (side or "BUY").upper()
        if side not in ("BUY", "SELL"):
            return None
        qty = int(qty)
        if qty <= 0:
            return None
        self._order_id += 1
        order_id = f"sim_{self._order_id}"
        if price is None and self.mode == "simulation":
            price = 0.0
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "side": side,
            "price": price,
            "status": "filled",
        }
        self._orders[order_id] = order
        if self.mode == "simulation" and price and price > 0:
            cost = qty * price
            if side == "BUY":
                self._balance["cash"] -= cost
                pos = self._positions.get(symbol, {"qty": 0, "avg_price": 0, "market_value": 0})
                old_qty, old_avg = pos["qty"], pos.get("avg_price", 0)
                new_qty = old_qty + qty
                new_avg = (old_qty * old_avg + qty * price) / new_qty if new_qty else 0
                self._positions[symbol] = {"qty": new_qty, "avg_price": new_avg, "market_value": new_qty * price}
            else:
                self._balance["cash"] += cost
                pos = self._positions.get(symbol, {"qty": 0})
                new_qty = pos["qty"] - qty
                if new_qty <= 0:
                    self._positions.pop(symbol, None)
                else:
                    self._positions[symbol] = {**pos, "qty": new_qty}
            mv_sum = sum(
                p.get("market_value", p.get("qty", 0) * p.get("avg_price", 0))
                for p in self._positions.values()
            )
            self._balance["total_asset"] = self._balance["cash"] + mv_sum
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self._orders and self._orders[order_id].get("status") == "submitted":
            self._orders[order_id]["status"] = "cancelled"
            return True
        return False
