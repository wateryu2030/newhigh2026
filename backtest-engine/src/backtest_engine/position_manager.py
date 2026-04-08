# Auto-fixed by Cursor on 2026-04-02: PositionManager and stop/take-profit helpers.
"""Position sizing: fixed fraction, Kelly, vol inverse; optional stop/take-profit on signals."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

_log = logging.getLogger(__name__)


@dataclass
class PositionManager:
    lot_size: int = 100

    def position_sizing(
        self,
        equity: float,
        price: float,
        *,
        method: str = "fixed_fraction",
        fraction: float = 0.1,
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        daily_volatility: Optional[float] = None,
        target_vol: float = 0.15,
    ) -> int:
        try:
            equity = float(equity)
            price = float(price)
        except (TypeError, ValueError):
            _log.warning("position_sizing: invalid equity/price")
            return 0
        if equity <= 0 or price <= 0:
            return 0

        if method == "kelly" and win_rate is not None and avg_win and avg_loss:
            p = float(win_rate)
            al = float(avg_loss)
            r = abs(float(avg_win) / al) if al != 0 else 0.0
            k = p - (1.0 - p) / r if r > 0 else 0.0
            k = max(0.0, min(k, float(fraction)))
            notional = equity * k
        elif method == "vol_inverse" and daily_volatility is not None:
            vol = max(float(daily_volatility), 1e-6)
            notional = equity * min(1.0, float(target_vol) / vol)
        else:
            notional = equity * float(fraction)

        shares = int(notional // price)
        if self.lot_size > 1:
            shares = (shares // self.lot_size) * self.lot_size
        return max(0, shares)


def apply_stop_take_series(
    close: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    *,
    stop_loss_pct: Optional[float] = None,
    take_profit_pct: Optional[float] = None,
) -> tuple[pd.Series, pd.Series]:
    e = entries.reindex(close.index).fillna(False).astype(bool).copy()
    x = exits.reindex(close.index).fillna(False).astype(bool).copy()
    ref = np.nan
    in_pos = False
    for i in range(len(close.index)):
        price = float(close.iloc[i])
        if e.iloc[i]:
            in_pos = True
            ref = price
        if not in_pos:
            continue
        if stop_loss_pct is not None and ref and not np.isnan(ref) and ref > 0:
            if price <= ref * (1.0 - float(stop_loss_pct)):
                x.iloc[i] = True
                in_pos = False
                ref = np.nan
                continue
        if take_profit_pct is not None and ref and not np.isnan(ref) and ref > 0:
            if price >= ref * (1.0 + float(take_profit_pct)):
                x.iloc[i] = True
                in_pos = False
                ref = np.nan
                continue
        if x.iloc[i]:
            in_pos = False
            ref = np.nan
    return e, x
