# -*- coding: utf-8 -*-
"""
绩效分析器：胜率、盈亏比、最大回撤、夏普比率等，供情绪回测与龙虎榜统计使用。
"""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Sequence


def win_rate(returns: Sequence[float]) -> float:
    """胜率：收益为正的交易日占比。"""
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0)
    return wins / len(returns)


def avg_win_avg_loss(returns: Sequence[float]) -> tuple:
    """平均盈利、平均亏损（仅统计正/负收益）。"""
    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r < 0]
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = sum(losses) / len(losses) if losses else 0.0
    return avg_win, avg_loss


def profit_factor(returns: Sequence[float]) -> float:
    """盈亏比：总盈利/|总亏损|。"""
    total_win = sum(r for r in returns if r > 0)
    total_loss = abs(sum(r for r in returns if r < 0))
    if total_loss == 0:
        return 10.0 if total_win > 0 else 0.0
    return total_win / total_loss


def max_drawdown_from_returns(returns: Sequence[float]) -> float:
    """从收益率序列计算最大回撤（小数）。"""
    if not returns:
        return 0.0
    cum = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in returns:
        cum *= 1.0 + r
        if cum > peak:
            peak = cum
        if peak > 0:
            dd = (peak - cum) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def sharpe_annualized(
    returns: Sequence[float],
    risk_free_rate: float = 0.03,
    trading_days_per_year: int = 252,
) -> float:
    """年化夏普比率。"""
    if not returns or len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    var = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(var) if var > 0 else 1e-10
    excess = mean_r * trading_days_per_year - risk_free_rate
    if std <= 0:
        return 0.0
    return excess / (std * math.sqrt(trading_days_per_year))


def analyze_returns(
    returns: List[float],
    risk_free_rate: float = 0.03,
) -> Dict[str, Any]:
    """
    对收益率序列做完整绩效分析。
    :param returns: 日收益率列表（小数）
    :return: win_rate, avg_win, avg_loss, profit_factor, max_drawdown, sharpe, total_return
    """
    if not returns:
        return {
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
            "total_return": 0.0,
            "count": 0,
        }
    aw, al = avg_win_avg_loss(returns)
    total_return = 1.0
    for r in returns:
        total_return *= 1.0 + r
    total_return -= 1.0
    return {
        "win_rate": round(win_rate(returns), 4),
        "avg_win": round(aw, 6),
        "avg_loss": round(al, 6),
        "profit_factor": round(profit_factor(returns), 4),
        "max_drawdown": round(max_drawdown_from_returns(returns), 4),
        "sharpe": round(sharpe_annualized(returns, risk_free_rate=risk_free_rate), 4),
        "total_return": round(total_return, 4),
        "count": len(returns),
    }
