# -*- coding: utf-8 -*-
"""
VaR（风险价值）：私募级风控指标，日/周 VaR 与熔断阈值。
"""
from __future__ import annotations
from typing import List
import numpy as np


def var_historical(returns: List[float], confidence: float = 0.95) -> float:
    """
    历史法 VaR。returns 为日收益率序列，confidence=0.95 表示 95% 置信度。
    返回负值表示亏损（如 -0.02 表示 2% 最大可能亏损）。
    """
    if not returns:
        return 0.0
    arr = np.array(returns)
    q = 1.0 - confidence
    return float(np.quantile(arr, q))


def var_covariance(returns: List[float], confidence: float = 0.95) -> float:
    """方差-协方差法（正态假设）；不依赖 scipy，无则用近似分位数。"""
    if not returns:
        return 0.0
    arr = np.array(returns)
    mu = np.mean(arr)
    sigma = np.std(arr)
    if sigma <= 0:
        return 0.0
    try:
        from scipy import stats
        z = stats.norm.ppf(1.0 - confidence)
    except Exception:
        z = -1.645 if confidence >= 0.95 else -1.28
    return float(mu + z * sigma)


def check_var_breach(
    current_pnl_pct: float,
    var_limit_pct: float,
) -> tuple[bool, str]:
    """当日亏损是否超过 VaR 阈值（熔断）。"""
    if current_pnl_pct <= -abs(var_limit_pct):
        return False, f"VaR 熔断: 当日亏损 {current_pnl_pct*100:.2f}% 超过 {var_limit_pct*100}%"
    return True, "ok"
