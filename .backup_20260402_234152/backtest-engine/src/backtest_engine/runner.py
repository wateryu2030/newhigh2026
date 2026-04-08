"""Backtest runner using vectorbt."""

from typing import List, Optional

import numpy as np
import pandas as pd
import vectorbt as vbt

from core import OHLCV


def run_backtest(
    close: pd.Series,
    entries: pd.Series,
    exits: pd.Series,
    init_cash: float = 10000.0,
    fees: float = 0.001,
    freq: Optional[str] = "1h",
) -> vbt.Portfolio:
    """
    Run vectorized backtest from close prices and boolean entry/exit signals.
    Returns vectorbt Portfolio.
    """
    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        init_cash=init_cash,
        fees=fees,
        freq=freq,
    )
    return pf


def run_backtest_from_ohlcv(
    ohlcv_list: List[OHLCV],
    entries: List[bool],
    exits: List[bool],
    init_cash: float = 10000.0,
    fees: float = 0.001,
    interval: str = "1h",
) -> vbt.Portfolio:
    """Run backtest from OHLCV list and signal lists. entries/exits must match length of ohlcv_list."""
    if len(ohlcv_list) != len(entries) or len(ohlcv_list) != len(exits):
        raise ValueError("ohlcv_list, entries, exits must have same length")
    close = pd.Series(
        [b.close for b in ohlcv_list],
        index=pd.DatetimeIndex([b.timestamp for b in ohlcv_list]),
    )
    ent = pd.Series(entries, index=close.index)
    ex = pd.Series(exits, index=close.index)
    return run_backtest(close, ent, ex, init_cash=init_cash, fees=fees, freq=interval)
