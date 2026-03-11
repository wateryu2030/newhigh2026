"""ATR (Average True Range)."""
from typing import List, Union

import numpy as np
import pandas as pd

from core import OHLCV


def true_range(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
) -> np.ndarray:
    """TR = max(high - low, |high - prev_close|, |low - prev_close|)."""
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - prev_close),
            np.abs(low - prev_close),
        ),
    )
    return tr


def atr(
    high: Union[List[float], np.ndarray],
    low: Union[List[float], np.ndarray],
    close: Union[List[float], np.ndarray],
    period: int = 14,
) -> np.ndarray:
    """ATR = EMA(True Range, period). First period-1 values are NaN."""
    if isinstance(high, list):
        high = np.array(high, dtype=float)
    if isinstance(low, list):
        low = np.array(low, dtype=float)
    if isinstance(close, list):
        close = np.array(close, dtype=float)
    tr = true_range(high, low, close)
    atr_arr = pd.Series(tr).ewm(span=period, adjust=False).mean().values
    return atr_arr


def atr_from_ohlcv(bars: List[OHLCV], period: int = 14) -> np.ndarray:
    """Compute ATR from OHLCV bars."""
    high = np.array([b.high for b in bars])
    low = np.array([b.low for b in bars])
    close = np.array([b.close for b in bars])
    return atr(high, low, close, period=period)
