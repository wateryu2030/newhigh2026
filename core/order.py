# -*- coding: utf-8 -*-
"""
订单状态机与订单结构：机构风控与执行层通用。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class OrderStatus(str, Enum):
    """订单状态流转：SUBMITTED -> FILLED / CANCELLED / REJECTED；可扩展 PARTIAL_FILLED。"""
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """统一订单结构。"""
    order_id: str
    symbol: str
    side: str  # BUY | SELL
    qty: float
    price: Optional[float]  # None 表示市价
    order_type: str = "limit"  # limit | market
    status: OrderStatus = OrderStatus.SUBMITTED
    filled_qty: float = 0.0
    filled_avg_price: Optional[float] = None
    created_at: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "price": self.price,
            "order_type": self.order_type,
            "status": self.status.value,
            "filled_qty": self.filled_qty,
            "filled_avg_price": self.filled_avg_price,
            "created_at": self.created_at,
            **self.extra,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Order:
        status = d.get("status", "submitted")
        if isinstance(status, str) and status.upper() in OrderStatus.__members__:
            status = OrderStatus(status.lower())
        else:
            status = OrderStatus.SUBMITTED
        return cls(
            order_id=str(d.get("order_id", "")),
            symbol=str(d.get("symbol", "")),
            side=(d.get("side") or "BUY").upper(),
            qty=float(d.get("qty", 0)),
            price=float(d["price"]) if d.get("price") is not None else None,
            order_type=str(d.get("order_type", "limit")),
            status=status,
            filled_qty=float(d.get("filled_qty", 0)),
            filled_avg_price=float(d["filled_avg_price"]) if d.get("filled_avg_price") is not None else None,
            created_at=d.get("created_at"),
            extra={k: v for k, v in d.items() if k not in (
                "order_id", "symbol", "side", "qty", "price", "order_type",
                "status", "filled_qty", "filled_avg_price", "created_at"
            )},
        )
