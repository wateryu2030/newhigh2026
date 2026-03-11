"""Mean reversion strategy: RSI / Bollinger oversold-overbought."""
from typing import List, Tuple

import numpy as np

from core import OHLCV, Signal


def _rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
    n = len(closes)
    out = np.full(n, np.nan)
    if n < period + 1:
        return out
    delta = np.diff(closes)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_gain = np.zeros(n)
    avg_loss = np.zeros(n)
    avg_gain[period] = np.mean(gain[:period])
    avg_loss[period] = np.mean(loss[:period])
    for i in range(period + 1, n):
        avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gain[i - 1]) / period
        avg_loss[i] = (avg_loss[i - 1] * (period - 1) + loss[i - 1]) / period
    rs = np.where(avg_loss != 0, avg_gain / avg_loss, np.inf)
    out[period:] = 100 - (100 / (1 + rs[period:]))
    return out


def mean_reversion_signals(
    ohlcv_list: List[OHLCV],
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> List[Signal]:
    """
    BUY when RSI < oversold, SELL when RSI > overbought. HOLD otherwise.
    """
    closes = np.array([b.close for b in ohlcv_list], dtype=float)
    rsi_arr = _rsi(closes, period=rsi_period)
    signals = []
    for i in range(len(closes)):
        if np.isnan(rsi_arr[i]):
            signals.append(Signal.HOLD)
        elif rsi_arr[i] < oversold:
            signals.append(Signal.BUY)
        elif rsi_arr[i] > overbought:
            signals.append(Signal.SELL)
        else:
            signals.append(Signal.HOLD)
    return signals


def mean_reversion_entries_exits(
    ohlcv_list: List[OHLCV],
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> Tuple[List[bool], List[bool]]:
    """Return (entries, exits) for backtest."""
    sigs = mean_reversion_signals(
        ohlcv_list, rsi_period=rsi_period, oversold=oversold, overbought=overbought
    )
    return [s == Signal.BUY for s in sigs], [s == Signal.SELL for s in sigs]
