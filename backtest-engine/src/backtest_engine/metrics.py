"""Backtest metrics: Sharpe, Sortino, MaxDrawdown, WinRate, ProfitFactor. Output: JSON."""
from typing import Any, Dict, Optional

import pandas as pd
import vectorbt as vbt


def compute_metrics(
    pf: vbt.Portfolio,
    freq: Optional[str] = "1h",
) -> Dict[str, Any]:
    """
    Extract Sharpe, Sortino, MaxDrawdown, WinRate, ProfitFactor from vectorbt Portfolio.
    Returns a JSON-serializable dict.
    """
    settings = dict(freq=freq) if freq else {}
    try:
        stats = pf.stats(settings=settings)
    except Exception:
        stats = pf.stats()

    if isinstance(stats, pd.Series):
        s = stats
    else:
        s = stats.iloc[0] if hasattr(stats, "iloc") else stats

    # vectorbt stats use different naming; try common variants
    sharpe = None
    sortino = None
    max_dd = None
    win_rate = None
    profit_factor = None
    for name, val in s.items():
        n = str(name).lower()
        if "sharpe" in n:
            sharpe = float(val) if pd.notna(val) else None
        elif "sortino" in n:
            sortino = float(val) if pd.notna(val) else None
        elif "max drawdown" in n or "max_drawdown" in n:
            max_dd = float(val) if pd.notna(val) else None
        elif "win rate" in n or "win_rate" in n:
            win_rate = float(val) if pd.notna(val) else None
        elif "profit factor" in n or "profit_factor" in n:
            profit_factor = float(val) if pd.notna(val) else None

    # Fallbacks: use portfolio methods if available
    if sharpe is None and hasattr(pf, "sharpe_ratio"):
        try:
            sr = pf.sharpe_ratio()
            sharpe = float(sr.iloc[0]) if hasattr(sr, "iloc") else float(sr)
        except Exception:
            pass
    if sortino is None and hasattr(pf, "sortino_ratio"):
        try:
            sor = pf.sortino_ratio()
            sortino = float(sor.iloc[0]) if hasattr(sor, "iloc") else float(sor)
        except Exception:
            pass
    if max_dd is None and hasattr(pf, "max_drawdown"):
        try:
            md = pf.max_drawdown()
            max_dd = float(md.iloc[0]) if hasattr(md, "iloc") else float(md)
        except Exception:
            pass

    # Win rate / profit factor from trades
    try:
        trades = pf.trades.records_readable
        if trades is not None and len(trades) > 0:
            if "PnL" in trades.columns:
                wins = (trades["PnL"] > 0).sum()
                losses = (trades["PnL"] <= 0).sum()
                if wins + losses > 0:
                    win_rate = 100.0 * wins / (wins + losses)
                gross_profit = trades.loc[trades["PnL"] > 0, "PnL"].sum()
                gross_loss = abs(trades.loc[trades["PnL"] < 0, "PnL"].sum())
                if gross_loss != 0:
                    profit_factor = float(gross_profit / gross_loss)
                else:
                    profit_factor = float(gross_profit) if gross_profit != 0 else None
    except Exception:
        pass

    return {
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "total_return": float(pf.total_return()) if hasattr(pf, "total_return") else None,
        "total_profit": float(pf.total_profit()) if hasattr(pf, "total_profit") else None,
    }
