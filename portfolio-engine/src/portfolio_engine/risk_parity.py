"""Risk parity allocation: weight inversely proportional to volatility."""

from typing import List

import numpy as np


def risk_parity_weights(volatilities: dict) -> dict:
    """
    volatilities: symbol -> annualized vol (e.g. 0.2 for 20%).
    Weight proportional to 1/vol; normalized to sum to 1.
    """
    if not volatilities:
        return {}
    inv_vol = {s: 1.0 / max(v, 1e-8) for s, v in volatilities.items()}
    total = sum(inv_vol.values())
    return {s: inv_vol[s] / total for s in inv_vol}


def risk_parity_weights_from_returns(returns: dict) -> dict:
    """Compute vol from returns (columns = symbols), then risk parity weights."""
    if not returns:
        return {}
    vols = {}
    for s, r in returns.items():
        arr = np.asarray(r, dtype=float)
        arr = arr[~np.isnan(arr)]
        if len(arr) < 2:
            vols[s] = 1.0
        else:
            vols[s] = np.std(arr) * np.sqrt(252)  # annualized
    return risk_parity_weights(vols)


def risk_parity_position_sizes(
    volatilities: dict,
    capital: float,
) -> dict:
    """Position size per symbol in notional."""
    w = risk_parity_weights(volatilities)
    return {s: capital * w[s] for s in w}
