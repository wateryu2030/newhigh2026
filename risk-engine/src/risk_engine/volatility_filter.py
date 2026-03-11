"""Volatility filter: disable or scale when volatility too high."""
from typing import List, Union

import numpy as np


def volatility_annualized(returns: Union[List[float], np.ndarray], periods_per_year: int = 252) -> float:
    """Annualized volatility of returns."""
    r = np.asarray(returns, dtype=float)
    r = r[~np.isnan(r)]
    if len(r) < 2:
        return 0.0
    return float(np.std(r) * np.sqrt(periods_per_year))


def volatility_ok(
    returns: Union[List[float], np.ndarray],
    max_volatility: float = 0.5,
    periods_per_year: int = 252,
) -> bool:
    """True if annualized vol <= max_volatility (e.g. 0.5 = 50%)."""
    return volatility_annualized(returns, periods_per_year) <= max_volatility


def should_disable_strategy_volatility(
    returns: Union[List[float], np.ndarray],
    max_volatility: float = 0.5,
    periods_per_year: int = 252,
) -> bool:
    """True if strategy should be disabled (vol too high)."""
    return not volatility_ok(returns, max_volatility, periods_per_year)
