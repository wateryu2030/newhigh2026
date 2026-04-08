# Auto-fixed by Cursor on 2026-04-02: SlippageModel and CommissionModel for backtests.
"""Backtest cost models: commission and slippage combined for vectorbt fees."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CommissionModel:
    """Per-leg commission as fraction of trade value (default 0.02%)."""

    rate_per_leg: float = 0.0002

    @classmethod
    def default(cls) -> CommissionModel:
        return cls(rate_per_leg=0.0002)


@dataclass
class SlippageModel:
    """Per-leg slippage as fraction of price (default 0.1%)."""

    rate_per_leg: float = 0.001

    @classmethod
    def default(cls) -> SlippageModel:
        return cls(rate_per_leg=0.001)


def effective_fee_per_order(
    commission: CommissionModel | None = None,
    slippage: SlippageModel | None = None,
) -> float:
    """Single fee rate passed to vectorbt per order (buy or sell leg)."""
    c = commission or CommissionModel.default()
    s = slippage or SlippageModel.default()
    return float(c.rate_per_leg) + float(s.rate_per_leg)
