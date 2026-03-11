"""Rebalance: compute target positions from weights and current positions."""
from typing import Dict


def rebalance(
    weights: Dict[str, float],
    prices: Dict[str, float],
    capital: float,
    current_positions: Dict[str, float],
) -> Dict[str, float]:
    """
    Target position in units per symbol.
    weights: symbol -> weight (sum 1), prices: symbol -> price, current_positions: symbol -> units.
    Returns symbol -> target_units (signed; positive = long).
    """
    targets = {}
    for s, w in weights.items():
        price = prices.get(s) or 1.0
        if price <= 0:
            continue
        target_notional = capital * w
        target_units = target_notional / price
        targets[s] = target_units
    return targets


def rebalance_deltas(
    weights: Dict[str, float],
    prices: Dict[str, float],
    capital: float,
    current_positions: Dict[str, float],
) -> Dict[str, float]:
    """Return delta units to trade: target_units - current_units."""
    targets = rebalance(weights, prices, capital, current_positions)
    return {
        s: targets[s] - current_positions.get(s, 0.0)
        for s in targets
    }
