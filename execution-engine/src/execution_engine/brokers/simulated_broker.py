"""模拟盘经纪：委托 execution_engine.simulated 执行，无真实下单。"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import BaseBroker, OrderResult, PositionInfo

_log = logging.getLogger(__name__)


class SimulatedBroker(BaseBroker):
    """通过 step_simulated / get_positions 等与 DuckDB 模拟盘交互；单次下单可视为调用 step 的简化。"""

    def submit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        **kwargs: Any,
    ) -> OrderResult:
        try:
            from execution_engine.simulated import step_simulated, get_orders

            step = step_simulated(lot_size=int(quantity), max_buys=1, max_sells=1)
            orders = get_orders(limit=1)
            oid = str(orders[0].get("id")) if orders else None
            return OrderResult(ok=step.get("ok", False), order_id=oid, message=step.get("error"))
        except Exception as e:
            _log.exception("SimulatedBroker.submit_order failed for %s", symbol)
            return OrderResult(ok=False, message=str(e))

    def cancel_order(self, symbol: str, order_id: str, **kwargs: Any) -> OrderResult:
        return OrderResult(ok=True, order_id=order_id, message="simulated cancel no-op")

    def get_positions(self, **kwargs: Any) -> List[PositionInfo]:
        try:
            from execution_engine.simulated import get_positions

            rows = get_positions(limit=500)
            return [
                PositionInfo(
                    symbol=r.get("code", ""),
                    side=r.get("side", "LONG"),
                    quantity=float(r.get("qty", 0)),
                    avg_price=(
                        float(r.get("avg_price", 0)) if r.get("avg_price") is not None else None
                    ),
                )
                for r in rows
            ]
        except Exception:
            _log.exception("SimulatedBroker.get_positions failed")
            return []

    def get_orders(
        self, symbol: Optional[str] = None, limit: int = 100, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        try:
            from execution_engine.simulated import get_orders

            return get_orders(limit=limit)
        except Exception:
            _log.exception("SimulatedBroker.get_orders failed")
            return []
