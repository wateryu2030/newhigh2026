"""Feature pipeline: OHLCV -> RSI, MACD, VWAP, ATR, Momentum, Volatility -> feature matrix."""

from typing import List, Optional

import numpy as np
import pandas as pd

from core import OHLCV
from .rsi import rsi
from .macd import macd
from .vwap import vwap
from .atr import atr


def momentum_returns(closes: np.ndarray, period: int = 10) -> np.ndarray:
    """Momentum: (close - close_shift(period)) / close_shift(period)."""
    c = np.asarray(closes, dtype=float)
    out = np.full(len(c), np.nan)
    if len(c) <= period:
        return out
    out[period:] = (c[period:] - c[:-period]) / np.where(c[:-period] != 0, c[:-period], np.nan)
    return out


def volatility_returns(closes: np.ndarray, period: int = 20) -> np.ndarray:
    """Volatility: rolling std of returns."""
    c = np.asarray(closes, dtype=float)
    ret = np.diff(c) / np.where(c[:-1] != 0, c[:-1], np.nan)
    out = np.full(len(c), np.nan)
    if len(ret) < period:
        return out
    for i in range(period - 1, len(ret)):
        out[i + 1] = np.nanstd(ret[i - period + 1 : i + 1])
    return out


def build_feature_matrix(
    ohlcv_list: List[OHLCV],
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    atr_period: int = 14,
    momentum_period: int = 10,
    volatility_period: int = 20,
) -> pd.DataFrame:
    """
    Build feature matrix from OHLCV list.
    Columns: timestamp, open, high, low, close, volume, rsi, macd, macd_signal, macd_hist, vwap, atr, momentum, volatility.
    """
    if not ohlcv_list:
        return pd.DataFrame()

    n = len(ohlcv_list)
    timestamps = [b.timestamp for b in ohlcv_list]
    closes = np.array([b.close for b in ohlcv_list])
    highs = np.array([b.high for b in ohlcv_list])
    lows = np.array([b.low for b in ohlcv_list])
    volumes = np.array([b.volume for b in ohlcv_list])

    rsi_arr = rsi(ohlcv_list, period=rsi_period)
    macd_line, macd_sig, macd_hist = macd(
        ohlcv_list, fast=macd_fast, slow=macd_slow, signal_period=macd_signal
    )
    vwap_arr = vwap(ohlcv_list)
    atr_arr = atr(ohlcv_list, period=atr_period)
    mom_arr = momentum_returns(closes, period=momentum_period)
    vol_arr = volatility_returns(closes, period=volatility_period)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": [b.open for b in ohlcv_list],
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "rsi": rsi_arr,
            "macd": macd_line,
            "macd_signal": macd_sig,
            "macd_hist": macd_hist,
            "vwap": vwap_arr,
            "atr": atr_arr,
            "momentum": mom_arr,
            "volatility": vol_arr,
        }
    )
    return df
