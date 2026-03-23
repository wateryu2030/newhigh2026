"""Breakout strategy: price breaks N-period high/low."""

from typing import List, Tuple

import numpy as np

from core import OHLCV, Signal


def breakout_signals(
    ohlcv_list: List[OHLCV],
    lookback: int = 20,
) -> List[Signal]:
    """
    BUY when close > max(high of lookback), SELL when close < min(low of lookback).
    HOLD otherwise.
    """
    highs = np.array([b.high for b in ohlcv_list], dtype=float)
    lows = np.array([b.low for b in ohlcv_list], dtype=float)
    closes = np.array([b.close for b in ohlcv_list], dtype=float)
    n = len(closes)
    signals = [Signal.HOLD] * n
    if n < lookback + 1:
        return signals

    for i in range(lookback, n):
        highest = np.max(highs[i - lookback : i])
        lowest = np.min(lows[i - lookback : i])
        if closes[i] > highest:
            signals[i] = Signal.BUY
        elif closes[i] < lowest:
            signals[i] = Signal.SELL
    return signals


def breakout_entries_exits(
    ohlcv_list: List[OHLCV],
    lookback: int = 20,
) -> Tuple[List[bool], List[bool]]:
    """Return (entries, exits) for backtest."""
    sigs = breakout_signals(ohlcv_list, lookback=lookback)
    return [s == Signal.BUY for s in sigs], [s == Signal.SELL for s in sigs]
