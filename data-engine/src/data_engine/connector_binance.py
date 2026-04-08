"""Binance connector: fetch klines and normalize to OHLCV."""

import datetime as dt
from typing import List

import requests

from core import OHLCV


def _interval_to_binance(interval: str) -> str:
    """Map internal interval to Binance kline interval."""
    return interval  # 1m, 5m, 1h, 1d are supported as-is


def fetch_klines(  # pylint: disable=too-many-positional-arguments
    symbol: str,
    interval: str,
    limit: int = 500,
    start_time: int | None = None,
    end_time: int | None = None,
    base_url: str = "https://api.binance.com",
) -> List[OHLCV]:
    """
    Fetch OHLCV klines from Binance and normalize to OHLCV.
    """
    url = f"{base_url}/api/v3/klines"
    params = {
        "symbol": symbol.replace("/", "").upper(),  # BTCUSDT
        "interval": _interval_to_binance(interval),
        "limit": min(limit, 1000),
    }
    if start_time is not None:
        params["startTime"] = start_time
    if end_time is not None:
        params["endTime"] = end_time

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()

    result = []
    for r in rows:
        ts, o, h, l, c, v = r[0], float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[5])
        result.append(
            OHLCV(
                symbol=symbol,
                timestamp=dt.datetime.fromtimestamp(ts / 1000, tz=dt.timezone.utc),
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
                interval=interval,
            )
        )
    return result
