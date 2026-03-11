"""RSI (Relative Strength Index) indicator."""
from typing import List, Union

import numpy as np

from core import OHLCV


def rsi_from_prices(closes: Union[List[float], np.ndarray], period: int = 14) -> np.ndarray:
    """Compute RSI from close prices. Returns array same length as closes; first period values are NaN."""
    c = np.asarray(closes, dtype=float)
    n = len(c)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    delta = np.diff(c)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.zeros(n)
    avg_loss = np.zeros(n)
    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])
    for i in range(period + 1, n):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i - 1]) / period
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = np.where(avg_loss != 0, avg_gain / avg_loss, np.inf)
    out[period:] = 100 - (100 / (1 + rs[period:]))
    return out


def rsi(ohlcv_list: List[OHLCV], period: int = 14) -> np.ndarray:
    """Compute RSI from OHLCV list."""
    closes = [b.close for b in ohlcv_list]
    return rsi_from_prices(closes, period=period)
