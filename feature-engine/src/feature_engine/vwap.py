"""VWAP (Volume Weighted Average Price) indicator."""
from typing import List

import numpy as np

from core import OHLCV


def vwap_from_ohlc(high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray) -> np.ndarray:
    """Compute typical price VWAP per bar (cumulative). Typical price = (H+L+C)/3."""
    typical = (high + low + close) / 3.0
    vol = np.asarray(volume, dtype=float)
    vol[vol == 0] = np.nan
    cum_tpv = np.nancumsum(typical * vol)
    cum_vol = np.nancumsum(vol)
    out = np.full(len(typical), np.nan)
    np.divide(cum_tpv, cum_vol, out=out, where=cum_vol != 0)
    return out


def vwap(ohlcv_list: List[OHLCV]) -> np.ndarray:
    """Compute cumulative VWAP from OHLCV list (one value per bar)."""
    high = np.array([b.high for b in ohlcv_list])
    low = np.array([b.low for b in ohlcv_list])
    close = np.array([b.close for b in ohlcv_list])
    volume = np.array([b.volume for b in ohlcv_list])
    return vwap_from_ohlc(high, low, close, volume)
