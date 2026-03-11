"""统一交易经纪抽象：下单、撤单、查持仓。"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OrderResult:
    ok: bool
    order_id: Optional[str] = None
    message: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class PositionInfo:
    symbol: str
    side: str
    quantity: float
    avg_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None


class BaseBroker(ABC):
    """实盘/模拟盘统一接口。"""

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        **kwargs: Any,
    ) -> OrderResult:
        """提交订单。side: BUY | SELL；order_type: MARKET | LIMIT。"""
        ...

    @abstractmethod
    def cancel_order(self, symbol: str, order_id: str, **kwargs: Any) -> OrderResult:
        """撤单。"""
        ...

    @abstractmethod
    def get_positions(self, **kwargs: Any) -> List[PositionInfo]:
        """当前持仓列表。"""
        ...

    def get_orders(self, symbol: Optional[str] = None, limit: int = 100, **kwargs: Any) -> List[Dict[str, Any]]:
        """订单列表（可选）。"""
        return []
