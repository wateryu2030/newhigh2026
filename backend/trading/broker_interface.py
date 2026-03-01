# -*- coding: utf-8 -*-
"""
券商接口抽象：支持模拟模式与真实模式，统一 connect / get_balance / get_positions / buy / sell / cancel_order。
订单状态见 order_state：NEW → SUBMITTED → PARTIAL_FILLED / FILLED / CANCELLED / REJECTED。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .order_state import OrderStatus, NEW, SUBMITTED, status_to_str, str_to_status


class Broker(ABC):
    """
    券商接口：模拟模式（默认）使用内存状态；真实模式需接入具体券商 API。
    """

    def __init__(self, mode: str = "simulation"):
        """
        mode: "simulation" 模拟模式 | "live" 真实模式
        """
        self.mode = (mode or "simulation").strip().lower()
        self._connected = False
        self._sim_balance: Dict[str, Any] = {}
        self._sim_positions: Dict[str, Dict[str, Any]] = {}
        self._sim_orders: Dict[str, Dict[str, Any]] = {}
        self._order_id = 0

    def buy(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        """买入。order_type: limit | market。"""
        return self.send_order(symbol=symbol, qty=qty, price=price, side="BUY", order_type=order_type)

    def sell(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        """卖出。order_type: limit | market。"""
        return self.send_order(symbol=symbol, qty=qty, price=price, side="SELL", order_type=order_type)

    def query_position(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """查询持仓。symbol 为空时返回全部持仓。"""
        positions = self.get_positions()
        if symbol is None:
            return positions
        # 支持模糊匹配
        out = {}
        for k, v in positions.items():
            if k == symbol or k.split(".")[0] == symbol or symbol in k:
                out[k] = v
        return out

    def connect(self) -> bool:
        """建立连接。模拟模式直接成功；真实模式可在此初始化券商 API。"""
        if self.mode == "live":
            # 真实模式：在此接入券商 API 登录等
            self._connected = True
            return True
        self._connected = True
        if not self._sim_balance:
            self._sim_balance = {"total_asset": 1000000.0, "cash": 1000000.0, "frozen": 0.0}
        return True

    def get_balance(self) -> Dict[str, Any]:
        """获取资金。模拟模式返回内存；真实模式调用券商查询。"""
        if not self._connected:
            self.connect()
        if self.mode == "live":
            return self._get_balance_live()
        return dict(self._sim_balance)

    def _get_balance_live(self) -> Dict[str, Any]:
        """真实模式：调用券商 API 查询资金。此处占位，接入时实现。"""
        return {"total_asset": 0.0, "cash": 0.0, "frozen": 0.0}

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        """获取持仓。模拟模式返回内存；真实模式调用券商查询。"""
        if not self._connected:
            self.connect()
        if self.mode == "live":
            return self._get_positions_live()
        return dict(self._sim_positions)

    def _get_positions_live(self) -> Dict[str, Dict[str, Any]]:
        """真实模式：调用券商 API 查询持仓。此处占位。"""
        return {}

    def send_order(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        side: str = "BUY",
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        """
        下单。返回订单信息 dict（含 order_id, status 等）；失败返回 None。
        side: BUY | SELL
        order_type: limit | market
        """
        if not self._connected:
            self.connect()
        if self.mode == "live":
            return self._send_order_live(symbol, qty, price, side, order_type)
        self._order_id += 1
        order_id = f"sim_{self._order_id}"
        self._sim_orders[order_id] = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "side": side.upper(),
            "status": "submitted",
        }
        return self._sim_orders[order_id]

    def _send_order_live(
        self,
        symbol: str,
        qty: float,
        price: Optional[float],
        side: str,
        order_type: str,
    ) -> Optional[Dict[str, Any]]:
        """真实模式：调用券商 API 下单。此处占位。"""
        return None

    def cancel_order(self, order_id: str) -> bool:
        """撤单。"""
        if not self._connected:
            return False
        if self.mode == "live":
            return self._cancel_order_live(order_id)
        if order_id in self._sim_orders:
            self._sim_orders[order_id]["status"] = "cancelled"
            return True
        return False

    def _cancel_order_live(self, order_id: str) -> bool:
        """真实模式：调用券商 API 撤单。此处占位。"""
        return False

    def set_sim_balance(self, total_asset: float, cash: float, frozen: float = 0.0) -> None:
        """模拟模式：设置资金（测试用）。"""
        self._sim_balance["total_asset"] = total_asset
        self._sim_balance["cash"] = cash
        self._sim_balance["frozen"] = frozen

    def set_sim_positions(self, positions: Dict[str, Dict[str, Any]]) -> None:
        """模拟模式：设置持仓（测试用）。"""
        self._sim_positions = dict(positions)
