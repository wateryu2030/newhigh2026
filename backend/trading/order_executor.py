# -*- coding: utf-8 -*-
"""
订单执行：封装 place_order / cancel_order / query_order，内部通过 Broker 与日志写入 DuckDB。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .broker_interface import Broker


class OrderExecutor:
    """订单执行器：委托 Broker 下单/撤单/查单，并记录到 orders 表。"""

    def __init__(self, broker: Optional[Broker] = None):
        self.broker = broker or Broker(mode="simulation")
        self._order_log = []

    def place_order(self, symbol: str, qty: float, price: Optional[float] = None, side: str = "BUY") -> Optional[Dict[str, Any]]:
        """
        下单。side: BUY | SELL。
        返回订单信息 dict（含 order_id, status）；失败返回 None。
        """
        if not self.broker._connected:
            self.broker.connect()
        order_type = "market" if price is None else "limit"
        out = self.broker.send_order(symbol=symbol, qty=qty, price=price, side=side.upper(), order_type=order_type)
        if out:
            self._order_log.append(out)
            try:
                from .db_logger import log_order
                log_order(out, action="place")
            except Exception:
                pass
        return out

    def cancel_order(self, order_id: Optional[str] = None) -> bool:
        """
        撤单。若未传 order_id，则撤销最近一笔未成交订单（模拟逻辑）。
        """
        if order_id:
            ok = self.broker.cancel_order(order_id)
            if ok:
                try:
                    from .db_logger import log_order
                    log_order({"order_id": order_id}, action="cancel")
                except Exception:
                    pass
            return ok
        for o in reversed(self._order_log):
            if (o.get("status") or "").lower() in ("submitted", "pending"):
                return self.cancel_order(o.get("order_id"))
        return False

    def query_order(self, order_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        查询订单。order_id 为空时返回当前会话已知订单列表；
        真实模式下可扩展为向券商查询单笔或列表。
        """
        if order_id:
            for o in self._order_log:
                if o.get("order_id") == order_id:
                    return [o]
            return []
        return list(self._order_log)
