# -*- coding: utf-8 -*-
"""
资金分配引擎：根据策略评分/风险分配资金。risk parity / mean variance / equal weight。
"""
from __future__ import annotations
from typing import Dict, List, Optional

import numpy as np


def allocate_equal_weight(strategy_ids: List[str]) -> Dict[str, float]:
    """等权：每个策略分配 1/n。"""
    if not strategy_ids:
        return {}
    w = 1.0 / len(strategy_ids)
    return {k: w for k in strategy_ids}


def allocate_risk_parity(
    strategy_ids: List[str],
    volatilities: Dict[str, float],
) -> Dict[str, float]:
    """
    风险平价：权重与波动率成反比，使各策略风险贡献相近。
    volatilities: {strategy_id: 年化波动率}
    """
    if not strategy_ids or not volatilities:
        return allocate_equal_weight(strategy_ids)
    inv_vol = {k: 1.0 / (float(volatilities.get(k, 0.2)) + 1e-8) for k in strategy_ids}
    total = sum(inv_vol.values())
    if total <= 0:
        return allocate_equal_weight(strategy_ids)
    return {k: v / total for k, v in inv_vol.items()}


def allocate_mean_variance(
    strategy_ids: List[str],
    returns: Dict[str, float],
    volatilities: Dict[str, float],
    risk_aversion: float = 1.0,
) -> Dict[str, float]:
    """
    均值-方差：权重 ∝ return / (vol^2 * risk_aversion)，再归一化。
    """
    if not strategy_ids:
        return {}
    w = {}
    for k in strategy_ids:
        r = float(returns.get(k, 0) or 0)
        vol = float(volatilities.get(k, 0.2) or 0.2) + 1e-8
        w[k] = max(0.0, r / (vol * vol * risk_aversion))
    total = sum(w.values())
    if total <= 0:
        return allocate_equal_weight(strategy_ids)
    return {k: v / total for k, v in w.items()}


def allocate_by_score(strategy_weights: Dict[str, float]) -> Dict[str, float]:
    """直接使用策略评分得到的权重（已归一化）。"""
    if not strategy_weights:
        return {}
    total = sum(strategy_weights.values())
    if total <= 0:
        return {k: 1.0 / len(strategy_weights) for k in strategy_weights}
    return {k: v / total for k, v in strategy_weights.items()}


class CapitalAllocator:
    """资金分配器：支持 risk_parity / mean_variance / equal_weight。"""

    def __init__(self, method: str = "equal_weight"):
        self.method = method

    def allocate(
        self,
        strategy_ids: List[str],
        strategy_weights: Optional[Dict[str, float]] = None,
        volatilities: Optional[Dict[str, float]] = None,
        returns: Optional[Dict[str, float]] = None,
        risk_aversion: float = 1.0,
    ) -> Dict[str, float]:
        """
        返回各策略资金权重（和=1）。
        """
        if self.method == "equal_weight":
            return allocate_equal_weight(strategy_ids)
        if self.method == "risk_parity" and volatilities:
            return allocate_risk_parity(strategy_ids, volatilities)
        if self.method == "mean_variance" and returns and volatilities:
            return allocate_mean_variance(strategy_ids, returns, volatilities, risk_aversion)
        if strategy_weights:
            return allocate_by_score(strategy_weights)
        return allocate_equal_weight(strategy_ids)
