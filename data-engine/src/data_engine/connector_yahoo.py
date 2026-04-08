"""Yahoo Finance connector: fetch OHLCV and normalize to core.OHLCV."""

import datetime as dt
from typing import List

from core import OHLCV

try:
    import yfinance as yf
except ImportError:
    yf = None


def _interval_to_yahoo(interval: str) -> str:
    """Map internal interval to Yahoo: 1m, 5m, 1h, 1d -> 1m, 5m, 1h, 1d."""
    return interval


def fetch_klines_yahoo(  # pylint: disable=too-many-positional-arguments
    symbol: str,
    interval: str = "1d",
    limit: int = 500,
    period: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> List[OHLCV]:
    """
    Fetch OHLCV from Yahoo Finance and normalize to OHLCV.
    symbol: e.g. AAPL, BTC-USD. period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, max.
    """
    if yf is None:
        raise ImportError("yfinance is required: pip install yfinance")
    ticker = yf.Ticker(symbol)
    if period:
        hist = ticker.history(period=period, interval=_interval_to_yahoo(interval))
    else:
        hist = ticker.history(start=start, end=end, interval=_interval_to_yahoo(interval))
    if hist is None or hist.empty:
        return []
    hist = hist.tail(limit)
    result = []
    for ts, row in hist.iterrows():
        t = ts.timestamp() if hasattr(ts, "timestamp") else None
        ts_utc = (
            dt.datetime.fromtimestamp(t, tz=dt.timezone.utc)
            if t is not None
            else dt.datetime.now(dt.timezone.utc)
        )
        result.append(
            OHLCV(
                symbol=symbol,
                timestamp=ts_utc,
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row.get("Volume", 0) or 0),
                interval=interval,
            )
        )
    return result
