"""Order manager: fetch positions, aggregate place/cancel."""

from typing import Any, Dict, List, Optional

from core import Position
from .binance_orders import place_order, cancel_order, fetch_open_orders, _signed_request


def fetch_positions(
    base_url: str = "https://api.binance.com",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> List[Position]:
    """
    Fetch current positions (Binance futures or spot balances).
    Spot: use /api/v3/account to get balances; filter to non-zero.
    Returns list of Position (symbol, side, quantity, entry_price, unrealized_pnl).
    """
    import os

    api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
    api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
    if not api_key:
        return []
    # Spot account balances
    try:
        acc = _signed_request(
            "GET", "/api/v3/account", base_url=base_url, api_key=api_key, api_secret=api_secret
        )
    except Exception:
        return []
    positions = []
    for b in acc.get("balances", []):
        free = float(b.get("free", 0))
        locked = float(b.get("locked", 0))
        qty = free + locked
        if qty <= 0:
            continue
        asset = b.get("asset", "")
        if asset and asset != "USDT":
            positions.append(
                Position(
                    symbol=asset,
                    side="LONG",
                    quantity=qty,
                    entry_price=0.0,
                    unrealized_pnl=None,
                )
            )
    return positions


def place_market_buy(symbol: str, quantity: float, **kwargs) -> Dict[str, Any]:
    """Convenience: market buy."""
    return place_order(symbol, "BUY", order_type="MARKET", quantity=quantity, **kwargs)


def place_market_sell(symbol: str, quantity: float, **kwargs) -> Dict[str, Any]:
    """Convenience: market sell."""
    return place_order(symbol, "SELL", order_type="MARKET", quantity=quantity, **kwargs)


def cancel_all_open_orders(symbol: str, **kwargs) -> List[Dict[str, Any]]:
    """Cancel all open orders for symbol. Returns list of cancel responses."""
    open_orders = fetch_open_orders(symbol, **kwargs)
    results = []
    for o in open_orders:
        order_id = o.get("orderId")
        if order_id is not None:
            results.append(cancel_order(symbol, order_id, **kwargs))
    return results
