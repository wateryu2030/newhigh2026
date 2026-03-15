"""MACD (Moving Average Convergence Divergence) indicator."""

from typing import List, Tuple

import numpy as np

from core import OHLCV


def _ema(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(len(values), np.nan)
    if len(values) < period:
        return out
    mult = 2.0 / (period + 1)
    out[period - 1] = np.mean(values[:period])
    for i in range(period, len(values)):
        out[i] = (values[i] - out[i - 1]) * mult + out[i - 1]
    return out


def macd_from_prices(
    closes: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute MACD line, signal line, histogram. Returns (macd_line, signal_line, histogram)."""
    c = np.asarray(closes, dtype=float)
    ema_fast = _ema(c, fast)
    ema_slow = _ema(c, slow)
    macd_line = ema_fast - ema_slow
    macd_valid = macd_line[~np.isnan(macd_line)]
    signal_line = _ema(macd_valid, signal)
    # align signal_line back to same length (signal_line has len(macd_valid); first signal-1 are nan)
    sig_full = np.full_like(macd_line, np.nan)
    valid = np.where(~np.isnan(macd_line))[0]
    if len(valid) >= signal:
        sig_full[valid[signal - 1 :]] = signal_line[signal - 1 :]
    histogram = np.full_like(macd_line, np.nan)
    np.subtract(macd_line, sig_full, out=histogram, where=~np.isnan(sig_full))
    return macd_line, sig_full, histogram


def macd(
    ohlcv_list: List[OHLCV],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute MACD from OHLCV list. Returns (macd_line, signal_line, histogram)."""
    closes = np.array([b.close for b in ohlcv_list], dtype=float)
    return macd_from_prices(closes, fast=fast, slow=slow, signal=signal_period)
