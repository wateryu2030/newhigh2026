"""Equal weight allocation: 1/n per asset."""

from typing import List


def equal_weight_weights(symbols: List[str]) -> dict:
    """Return weight per symbol: each 1/n."""
    n = len(symbols)
    if n == 0:
        return {}
    w = 1.0 / n
    return {s: w for s in symbols}


def equal_weight_position_sizes(
    symbols: List[str],
    capital: float,
) -> dict:
    """Position size per symbol in notional (capital * weight)."""
    w = equal_weight_weights(symbols)
    return {s: capital * w[s] for s in symbols}
