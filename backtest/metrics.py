# -*- coding: utf-8 -*-
"""
回测指标：年化收益、夏普、最大回撤等。
"""
from __future__ import annotations
import math
from typing import List


def total_return(equity_curve: List[float]) -> float:
    if not equity_curve or equity_curve[0] <= 0:
        return 0.0
    return equity_curve[-1] / equity_curve[0] - 1.0


def max_drawdown(equity_curve: List[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def sharpe_ratio(returns: List[float], risk_free: float = 0.0, annualize: bool = True) -> float:
    if not returns:
        return 0.0
    n = len(returns)
    mean_r = sum(returns) / n
    var = sum((r - mean_r) ** 2 for r in returns) / n
    std = math.sqrt(var) if var > 0 else 1e-8
    sr = (mean_r - risk_free) / std
    if annualize and n > 0:
        sr *= math.sqrt(252)
    return sr
