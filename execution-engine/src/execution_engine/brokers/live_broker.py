"""实盘经纪：对接 Binance（或后续券商 API）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseBroker, OrderResult, PositionInfo


class LiveBroker(BaseBroker):
    """使用 execution_engine.order_manager 与 Binance 通信。"""

    def __init__(self, base_url: str = "https://api.binance.com", api_key: Optional[str] = None, api_secret: Optional[str] = None):
        import os
        self.base_url = base_url
        self.api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
        self.api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")

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
            from execution_engine.order_manager import place_market_buy, place_market_sell
            if side.upper() == "BUY":
                out = place_market_buy(symbol, quantity, base_url=self.base_url, api_key=self.api_key, api_secret=self.api_secret)
            else:
                out = place_market_sell(symbol, quantity, base_url=self.base_url, api_key=self.api_key, api_secret=self.api_secret)
            return OrderResult(
                ok=out.get("orderId") is not None or out.get("ok") is True,
                order_id=str(out.get("orderId", "") or out.get("order_id", "")),
                raw=out,
            )
        except Exception as e:
            return OrderResult(ok=False, message=str(e))

    def cancel_order(self, symbol: str, order_id: str, **kwargs: Any) -> OrderResult:
        try:
            from execution_engine.order_manager import cancel_order as do_cancel
            out = do_cancel(symbol, int(order_id) if order_id.isdigit() else order_id, base_url=self.base_url, api_key=self.api_key, api_secret=self.api_secret)
            return OrderResult(ok=True, order_id=order_id, raw=out)
        except Exception as e:
            return OrderResult(ok=False, message=str(e))

    def get_positions(self, **kwargs: Any) -> List[PositionInfo]:
        try:
            from execution_engine.order_manager import fetch_positions
            from core import Position
            positions: List[Position] = fetch_positions(base_url=self.base_url, api_key=self.api_key, api_secret=self.api_secret)
            return [
                PositionInfo(symbol=p.symbol, side=p.side or "LONG", quantity=p.quantity, avg_price=p.entry_price, unrealized_pnl=p.unrealized_pnl)
                for p in positions
            ]
        except Exception:
            return []
