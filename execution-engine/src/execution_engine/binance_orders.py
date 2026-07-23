"""Binance order execution: place_order, cancel_order (REST API)."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

_log = logging.getLogger(__name__)


def _generate_signature(query_string: str, api_secret: str) -> str:
    """Generate HMAC-SHA256 signature for Binance signed endpoints."""
    return hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _signed_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    base_url: str = "https://api.binance.com",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """Send signed request to Binance. Requires API key/secret for trading."""
    api_key = api_key or os.environ.get("BINANCE_API_KEY", "")
    api_secret = api_secret or os.environ.get("BINANCE_API_SECRET", "")
    params = dict(params or {})
    params["timestamp"] = int(time.time() * 1000)

    query_string = urlencode(params)
    signature = _generate_signature(query_string, api_secret) if api_secret else ""
    signed_query = f"{query_string}&signature={signature}"

    headers = {"X-MBX-APIKEY": api_key} if api_key else {}
    url = f"{base_url}{path}"
    if method.upper() == "GET":
        r = requests.get(f"{url}?{signed_query}", headers=headers, timeout=15)
    else:
        r = requests.request(method, f"{url}?{signed_query}", headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def place_order(
    symbol: str,
    side: str,
    order_type: str = "MARKET",
    quantity: Optional[float] = None,
    quote_order_qty: Optional[float] = None,
    base_url: str = "https://api.binance.com",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Place order. side: BUY/SELL. order_type: MARKET or LIMIT.
    For MARKET: quantity or quote_order_qty.
    """
    sym = symbol.replace("/", "").upper()
    params = {"symbol": sym, "side": side.upper(), "type": order_type}
    if quantity is not None:
        params["quantity"] = quantity
    if quote_order_qty is not None:
        params["quoteOrderQty"] = quote_order_qty
    return _signed_request(
        "POST",
        "/api/v3/order",
        params=params,
        base_url=base_url,
        api_key=api_key,
        api_secret=api_secret,
    )


def cancel_order(
    symbol: str,
    order_id: int,
    base_url: str = "https://api.binance.com",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """Cancel order by order_id."""
    sym = symbol.replace("/", "").upper()
    return _signed_request(
        "DELETE",
        "/api/v3/order",
        params={"symbol": sym, "orderId": order_id},
        base_url=base_url,
        api_key=api_key,
        api_secret=api_secret,
    )


def fetch_open_orders(
    symbol: str,
    base_url: str = "https://api.binance.com",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
) -> list:
    """Fetch open orders for symbol."""
    sym = symbol.replace("/", "").upper()
    return _signed_request(
        "GET",
        "/api/v3/openOrders",
        params={"symbol": sym},
        base_url=base_url,
        api_key=api_key,
        api_secret=api_secret,
    )
