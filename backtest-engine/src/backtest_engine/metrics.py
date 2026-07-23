"""Backtest metrics: Sharpe, Sortino, MaxDrawdown, WinRate, ProfitFactor. Output: JSON."""

from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import vectorbt as vbt


def _safe_float(val: Any) -> Optional[float]:
    """安全转换为 float，处理 ndarray / Series 等类型。Timedelta 返回 None（需用 fallback）。"""
    if val is None:
        return None
    if isinstance(val, pd.Timedelta):
        return None  # Timedelta 不是数值，交给 fallback 处理
    if isinstance(val, (pd.Series, np.ndarray)):
        v = val.iloc[0] if hasattr(val, "iloc") else val[0] if len(val) > 0 else None
        return _safe_float(v)
    try:
        f = float(val)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


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
            sharpe = _safe_float(val)
        elif "sortino" in n:
            sortino = _safe_float(val)
        elif "max drawdown" in n or "max_drawdown" in n:
            max_dd = _safe_float(val)
        elif "win rate" in n or "win_rate" in n:
            win_rate = _safe_float(val)
        elif "profit factor" in n or "profit_factor" in n:
            profit_factor = _safe_float(val)

    # Fallbacks: use portfolio methods if available
    if sharpe is None and hasattr(pf, "sharpe_ratio"):
        try:
            sharpe = _safe_float(pf.sharpe_ratio())
        except Exception:
            pass
    if sortino is None and hasattr(pf, "sortino_ratio"):
        try:
            sortino = _safe_float(pf.sortino_ratio())
        except Exception:
            pass
    if max_dd is None and hasattr(pf, "max_drawdown"):
        try:
            max_dd = _safe_float(pf.max_drawdown())
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
                    profit_factor = _safe_float(gross_profit / gross_loss)
                else:
                    profit_factor = _safe_float(gross_profit) if gross_profit != 0 else None
    except Exception:
        pass

    return {
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_dd,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "total_return": _safe_float(pf.total_return()) if hasattr(pf, "total_return") else None,
        "total_profit": _safe_float(pf.total_profit()) if hasattr(pf, "total_profit") else None,
    }
