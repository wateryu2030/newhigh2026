"""Drawdown control: disable strategy if drawdown exceeds threshold."""

from typing import List, Optional

import numpy as np


def current_drawdown(equity_curve: List[float]) -> float:
    """Current drawdown from peak: (peak - current) / peak. 0 if no peak or current >= peak."""
    if not equity_curve:
        return 0.0
    arr = np.asarray(equity_curve, dtype=float)
    peak = np.maximum.accumulate(arr)
    dd = np.where(peak > 0, (peak - arr) / peak, 0.0)
    return float(dd[-1]) if len(dd) else 0.0


def max_drawdown(equity_curve: List[float]) -> float:
    """Maximum drawdown over the series."""
    if not equity_curve:
        return 0.0
    arr = np.asarray(equity_curve, dtype=float)
    peak = np.maximum.accumulate(arr)
    dd = np.where(peak > 0, (peak - arr) / peak, 0.0)
    return float(np.max(dd))


def drawdown_ok(
    equity_curve: List[float],
    max_drawdown_pct: float = 0.1,
) -> bool:
    """True if current drawdown is within limit (e.g. max_drawdown_pct=0.1 -> 10% max)."""
    return current_drawdown(equity_curve) <= max_drawdown_pct


def should_disable_strategy_drawdown(
    equity_curve: List[float],
    max_drawdown_pct: float = 0.1,
) -> bool:
    """True if strategy should be disabled (drawdown > threshold)."""
    return not drawdown_ok(equity_curve, max_drawdown_pct)
