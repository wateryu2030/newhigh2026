"""MACD (Moving Average Convergence Divergence)."""
from typing import List, Tuple, Union

import numpy as np
import pandas as pd

from core import OHLCV


def macd(
    close: Union[List[float], np.ndarray, pd.Series],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute MACD line, signal line, and histogram.
    Returns (macd_line, signal_line, histogram). First slow-1 values are NaN.
    """
    if isinstance(close, list):
        close = np.array(close, dtype=float)
    elif isinstance(close, pd.Series):
        close = close.values
    ema_fast = pd.Series(close).ewm(span=fast, adjust=False).mean().values
    ema_slow = pd.Series(close).ewm(span=slow, adjust=False).mean().values
    macd_line = ema_fast - ema_slow
    signal_line = pd.Series(macd_line).ewm(span=signal, adjust=False).mean().values
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def macd_from_ohlcv(
    bars: List[OHLCV],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute MACD from OHLCV bars."""
    close = [b.close for b in bars]
    return macd(close, fast=fast, slow=slow, signal=signal)
