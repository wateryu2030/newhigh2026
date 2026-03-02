# -*- coding: utf-8 -*-
"""
AI 权重优化：过去 N 天各策略收益 → 夏普比率 → 按夏普比例分配策略权重，实现自我进化。
"""
from __future__ import annotations
import logging
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# 策略 id 与文档一致
STRATEGY_IDS = ["dragon_strategy", "trend_strategy", "mean_reversion"]


def compute_sharpe(
    returns: List[float],
    risk_free: float = 0.0,
    annualize: bool = True,
) -> float:
    """
    夏普比率。returns 为日度收益序列；无收益或全零返回 0。
    """
    if not returns:
        return 0.0
    arr = np.asarray(returns, dtype=float)
    arr = arr[~np.isnan(arr)]
    if len(arr) < 2:
        return 0.0
    mean_ret = np.mean(arr)
    std_ret = np.std(arr)
    if std_ret <= 0:
        return 0.0
    sharpe = (mean_ret - risk_free) / std_ret
    if annualize:
        sharpe = sharpe * np.sqrt(252)
    return float(sharpe)


def optimize_weights(
    strategy_returns: Dict[str, List[float]],
    min_weight: float = 0.10,
    risk_free: float = 0.0,
) -> Dict[str, float]:
    """
    根据各策略过去 N 天收益，按夏普比例分配权重（自我进化）。
    :param strategy_returns: {"dragon_strategy": [r1,r2,...], "trend_strategy": [...], ...}
    :param min_weight: 单策略最低权重，避免某策略被完全剔除
    :return: {"dragon_strategy": 0.4, "trend_strategy": 0.35, "mean_reversion": 0.25}
    """
    sharpe_scores: Dict[str, float] = {}
    for sid, rets in strategy_returns.items():
        s = compute_sharpe(rets, risk_free=risk_free)
        # 夏普可能为负，用 max(0, sharpe) 或 softmax 处理，这里用 max(0, s) + 1e-6 保证可分配
        sharpe_scores[sid] = max(0.0, s) + 1e-6
    total = sum(sharpe_scores.values())
    if total <= 0:
        return {k: 1.0 / len(STRATEGY_IDS) for k in STRATEGY_IDS}
    weights = {k: v / total for k, v in sharpe_scores.items()}
    # 应用最低权重
    for k in weights:
        weights[k] = max(min_weight, weights[k])
    s = sum(weights.values())
    if s > 0:
        weights = {k: v / s for k, v in weights.items()}
    return weights
