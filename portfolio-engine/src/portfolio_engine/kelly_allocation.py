"""Kelly criterion allocation: fraction = (win_rate * payoff - (1 - win_rate)) / payoff."""
from typing import List, Optional


def kelly_fraction(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 1.0,
) -> float:
    """
    Full Kelly fraction. fraction=1 is full Kelly; 0.5 is half Kelly.
    win_rate in [0,1], avg_win/avg_loss typically positive.
    """
    if avg_loss == 0:
        return 0.0
    payoff = avg_win / abs(avg_loss)
    k = (win_rate * payoff - (1 - win_rate)) / payoff
    k = max(0.0, min(k, 1.0))
    return k * fraction


def kelly_weights(
    symbols: List[str],
    win_rates: dict,
    avg_wins: dict,
    avg_losses: dict,
    kelly_frac: float = 0.5,
) -> dict:
    """
    Per-symbol Kelly fraction as weight (normalized to sum to 1).
    win_rates, avg_wins, avg_losses: symbol -> value.
    """
    if not symbols:
        return {}
    kellys = {}
    for s in symbols:
        wr = win_rates.get(s, 0.5)
        aw = avg_wins.get(s, 1.0)
        al = avg_losses.get(s, 1.0)
        kellys[s] = kelly_fraction(wr, aw, al, fraction=kelly_frac)
    total = sum(kellys.values())
    if total <= 0:
        return equal_weight_weights(symbols) if symbols else {}
    return {s: kellys[s] / total for s in symbols}


def kelly_position_sizes(
    symbols: List[str],
    win_rates: dict,
    avg_wins: dict,
    avg_losses: dict,
    capital: float,
    kelly_frac: float = 0.5,
) -> dict:
    """Position size per symbol in notional."""
    from .equal_weight import equal_weight_weights
    w = kelly_weights(symbols, win_rates, avg_wins, avg_losses, kelly_frac=kelly_frac)
    if not w:
        w = equal_weight_weights(symbols)
    return {s: capital * w[s] for s in w}
