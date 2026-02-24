# -*- coding: utf-8 -*-
"""
AI 策略评分系统：收益率、夏普、最大回撤、胜率、稳定性 → 策略权重。
"""
from __future__ import annotations
from typing import Any, Dict, List

import numpy as np


def score_strategy(performance: Dict[str, Any]) -> float:
    """
    单策略综合评分 0~1。
    维度：收益率、夏普比率、最大回撤、胜率、稳定性。
    """
    ret = float(performance.get("return", 0) or 0)
    sharpe = float(performance.get("sharpe", 0) or 0)
    max_drawdown = float(performance.get("max_drawdown", 0.5) or 0.5)
    win_rate = float(performance.get("win_rate", 0.5) or 0.5)
    stability = float(performance.get("stability", 0.5) or 0.5)
    ret_score = min(1.0, max(0.0, (ret + 0.2) / 0.4))
    sharpe_score = min(1.0, max(0.0, (sharpe + 0.5) / 1.0))
    dd_score = 1.0 - min(1.0, max(0.0, max_drawdown))
    return 0.2 * ret_score + 0.25 * sharpe_score + 0.25 * dd_score + 0.15 * win_rate + 0.15 * stability


def compute_strategy_weights(
    performances: Dict[str, Dict[str, Any]],
    method: str = "score_based",
) -> Dict[str, float]:
    """
    根据各策略表现计算权重。
    performances: {strategy_id: {"return", "sharpe", "max_drawdown", "win_rate", "stability"}}
    method: "score_based" 按评分归一化 | "equal" 等权
    返回: {strategy_id: weight}, 和 1.
    """
    if not performances:
        return {}
    if method == "equal":
        w = 1.0 / len(performances)
        return {k: w for k in performances}
    scores = {k: score_strategy(v) for k, v in performances.items()}
    total = sum(scores.values())
    if total <= 0:
        return {k: 1.0 / len(scores) for k in scores}
    return {k: v / total for k, v in scores.items()}


class StrategyScorer:
    """策略评分器：可注入历史回测结果，输出权重。"""

    def __init__(self, method: str = "score_based"):
        self.method = method
        self._performance_cache: Dict[str, Dict[str, Any]] = {}

    def set_performance(self, strategy_id: str, performance: Dict[str, Any]) -> None:
        self._performance_cache[strategy_id] = performance

    def get_weights(self, strategy_ids: List[str] | None = None) -> Dict[str, float]:
        if strategy_ids is None:
            strategy_ids = list(self._performance_cache.keys())
        perfs = {sid: self._performance_cache.get(sid, {}) for sid in strategy_ids}
        return compute_strategy_weights(perfs, self.method)
