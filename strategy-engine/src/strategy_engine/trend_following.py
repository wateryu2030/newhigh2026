"""Trend following strategy: MA crossover, momentum."""

from typing import List, Tuple

import numpy as np

from core import OHLCV, Signal


def _sma(closes: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(closes), np.nan)
    if len(closes) < period:
        return out
    for i in range(period - 1, len(closes)):
        out[i] = np.mean(closes[i - period + 1 : i + 1])
    return out


def trend_following_signals(
    ohlcv_list: List[OHLCV],
    fast_period: int = 10,
    slow_period: int = 50,
) -> List[Signal]:
    """
    BUY when fast MA crosses above slow MA, SELL when fast crosses below slow.
    HOLD otherwise.
    """
    closes = np.array([b.close for b in ohlcv_list], dtype=float)
    n = len(closes)
    signals = [Signal.HOLD] * n
    if n < slow_period:
        return signals

    fast = _sma(closes, fast_period)
    slow = _sma(closes, slow_period)
    for i in range(1, n):
        if np.isnan(fast[i]) or np.isnan(slow[i]) or np.isnan(fast[i - 1]) or np.isnan(slow[i - 1]):
            continue
        if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i]:
            signals[i] = Signal.BUY
        elif fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            signals[i] = Signal.SELL
    return signals


def trend_following_entries_exits(
    ohlcv_list: List[OHLCV],
    fast_period: int = 10,
    slow_period: int = 50,
) -> Tuple[List[bool], List[bool]]:
    """Return (entries, exits) for backtest."""
    sigs = trend_following_signals(ohlcv_list, fast_period=fast_period, slow_period=slow_period)
    entries = [s == Signal.BUY for s in sigs]
    exits = [s == Signal.SELL for s in sigs]
    return entries, exits
