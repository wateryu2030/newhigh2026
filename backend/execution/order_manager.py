# -*- coding: utf-8 -*-
"""
订单管理：委托 BrokerAPI 下单、撤单、查询，并记录到 DuckDB。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .broker_api import BrokerAPI


class OrderManager:
    def __init__(self, broker: Optional[BrokerAPI] = None):
        self.broker = broker or BrokerAPI(mode="simulation")
        self._order_log: List[Dict[str, Any]] = []

    def place_order(self, symbol: str, qty: int, side: str, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        o = self.broker.place_order(symbol, qty, side, price)
        if o:
            self._order_log.append(o)
            self._log_to_db(o, "place")
        return o

    def cancel_order(self, order_id: str) -> bool:
        ok = self.broker.cancel_order(order_id)
        if ok:
            self._log_to_db({"order_id": order_id}, "cancel")
        return ok

    def query_orders(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if order_id:
            return [o for o in self._order_log if o.get("order_id") == order_id]
        return list(self._order_log)

    def _log_to_db(self, order: Dict[str, Any], action: str) -> None:
        try:
            from backend.data.duckdb_engine import get_engine
            eng = get_engine()
            if eng and hasattr(eng, "log_order"):
                eng.log_order(order, action)
        except Exception:
            pass
