# -*- coding: utf-8 -*-
"""
QMT 券商适配器占位：实盘接入 QMT 时在此实现。
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from .base import BrokerBase


class QMTBrokerAdapter(BrokerBase):
    """QMT 实盘：占位，后续对接 QMT API。"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._connected = False

    def connect(self) -> bool:
        # TODO: 连接 QMT
        self._connected = True
        return True

    def buy(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        if not self._connected:
            self.connect()
        # TODO: 调用 QMT 下单接口
        return {"symbol": symbol, "qty": int(qty), "side": "BUY", "status": "pending", "broker": "qmt"}

    def sell(
        self,
        symbol: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "limit",
    ) -> Optional[Dict[str, Any]]:
        if not self._connected:
            self.connect()
        # TODO: 调用 QMT 下单接口
        return {"symbol": symbol, "qty": int(qty), "side": "SELL", "status": "pending", "broker": "qmt"}

    def cancel_order(self, order_id: str) -> bool:
        # TODO: QMT 撤单
        return False

    def query_position(self, symbol: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        # TODO: QMT 查持仓
        return {}
