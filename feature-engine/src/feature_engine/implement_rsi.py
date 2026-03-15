"""RSI (Relative Strength Index)."""

from typing import List, Union

import numpy as np
import pandas as pd

from core import OHLCV


def rsi(close: Union[List[float], np.ndarray, pd.Series], period: int = 14) -> np.ndarray:
    """
    Compute RSI. Input: close prices. Output: RSI array (same length; first period-1 are NaN).
    """
    if isinstance(close, list):
        close = np.array(close, dtype=float)
    elif isinstance(close, pd.Series):
        close = close.values
    delta = np.diff(close, prepend=close[0])
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = pd.Series(gain).rolling(period, min_periods=period).mean().values
    avg_loss = pd.Series(loss).rolling(period, min_periods=period).mean().values
    rs = np.where(avg_loss == 0, 100.0, avg_gain / avg_loss)
    out = 100.0 - (100.0 / (1.0 + rs))
    return out


def rsi_from_ohlcv(bars: List[OHLCV], period: int = 14) -> np.ndarray:
    """Compute RSI from OHLCV bars."""
    close = [b.close for b in bars]
    return rsi(close, period=period)
