"""VWAP (Volume Weighted Average Price)."""

from typing import List, Union

import numpy as np
import pandas as pd

from core import OHLCV


def typical_price(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Typical price = (high + low + close) / 3."""
    return (high + low + close) / 3.0


def vwap(
    high: Union[List[float], np.ndarray],
    low: Union[List[float], np.ndarray],
    close: Union[List[float], np.ndarray],
    volume: Union[List[float], np.ndarray],
) -> np.ndarray:
    """
    VWAP = cumulative(typical_price * volume) / cumulative(volume).
    Returns VWAP per bar (running VWAP up to that bar).
    """
    if isinstance(high, list):
        high = np.array(high, dtype=float)
    if isinstance(low, list):
        low = np.array(low, dtype=float)
    if isinstance(close, list):
        close = np.array(close, dtype=float)
    if isinstance(volume, list):
        volume = np.array(volume, dtype=float)
    tp = typical_price(high, low, close)
    pv = tp * volume
    cum_pv = np.cumsum(pv)
    cum_vol = np.cumsum(volume)
    vwap_arr = np.where(cum_vol > 0, cum_pv / cum_vol, np.nan)
    return vwap_arr


def vwap_from_ohlcv(bars: List[OHLCV]) -> np.ndarray:
    """Compute VWAP from OHLCV bars."""
    high = np.array([b.high for b in bars])
    low = np.array([b.low for b in bars])
    close = np.array([b.close for b in bars])
    volume = np.array([b.volume for b in bars])
    return vwap(high, low, close, volume)
