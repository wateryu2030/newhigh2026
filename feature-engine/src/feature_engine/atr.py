"""ATR (Average True Range) indicator."""
from typing import List, Union

import numpy as np

from core import OHLCV


def atr_from_prices(
    high: Union[List[float], np.ndarray],
    low: Union[List[float], np.ndarray],
    close: Union[List[float], np.ndarray],
    period: int = 14,
) -> np.ndarray:
    """Compute ATR. True Range = max(H-L, |H-prev_C|, |L-prev_C|)."""
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    c = np.asarray(close, dtype=float)
    n = len(c)
    out = np.full(n, np.nan)
    if n < 2:
        return out
    prev_c = np.roll(c, 1)
    prev_c[0] = c[0]
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    if n < period:
        return out
    out[period - 1] = np.mean(tr[:period])
    for i in range(period, n):
        out[i] = (out[i - 1] * (period - 1) + tr[i]) / period
    return out


def atr(ohlcv_list: List[OHLCV], period: int = 14) -> np.ndarray:
    """Compute ATR from OHLCV list."""
    high = [b.high for b in ohlcv_list]
    low = [b.low for b in ohlcv_list]
    close = [b.close for b in ohlcv_list]
    return atr_from_prices(high, low, close, period=period)
