"""Exposure limit: cap total or per-symbol exposure."""

from typing import Dict


def total_exposure_notional(positions: Dict[str, float], prices: Dict[str, float]) -> float:
    """Total exposure in notional (absolute value of position * price)."""
    total = 0.0
    for s, qty in positions.items():
        p = prices.get(s, 0.0)
        total += abs(qty * p)
    return total


def exposure_ok(
    positions: Dict[str, float],
    prices: Dict[str, float],
    max_exposure: float,
) -> bool:
    """True if total notional exposure <= max_exposure."""
    return total_exposure_notional(positions, prices) <= max_exposure


def should_disable_strategy_exposure(
    positions: Dict[str, float],
    prices: Dict[str, float],
    max_exposure: float,
) -> bool:
    """True if strategy should be disabled (exposure over limit)."""
    return not exposure_ok(positions, prices, max_exposure)
