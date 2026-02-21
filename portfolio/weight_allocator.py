# -*- coding: utf-8 -*-
"""
权重分配器：等权 / 得分加权 / 风险平价。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
import numpy as np


class WeightAllocator:
    """
    为多策略分配权重。
    - equal_weight: 等权
    - score_weight: 按得分加权（得分越高权重越大）
    - risk_parity_weight: 风险平价（波动率倒数）
    """

    @staticmethod
    def equal_weight(strategies: List[Any]) -> List[float]:
        """等权。"""
        n = len(strategies)
        if n == 0:
            return []
        return [1.0 / n] * n

    @staticmethod
    def score_weight(
        strategies: List[Any],
        scores: Union[List[float], Dict[Any, float]],
    ) -> List[float]:
        """
        按得分加权。得分越高权重越大。
        :param scores: 与 strategies 顺序对应的得分列表，或 { strategy: score }
        """
        n = len(strategies)
        if n == 0:
            return []
        if isinstance(scores, dict):
            sc = [scores.get(s, 0.0) for s in strategies]
        else:
            sc = list(scores)[:n]
            sc.extend([0.0] * (n - len(sc)))
        sc = np.asarray(sc, dtype=float)
        sc = np.where(sc < 0, 0, sc)
        if sc.sum() <= 0:
            return [1.0 / n] * n
        w = sc / sc.sum()
        return w.tolist()

    @staticmethod
    def risk_parity_weight(
        strategies: List[Any],
        volatilities: Union[List[float], Dict[Any, float]],
    ) -> List[float]:
        """
        风险平价：按波动率倒数分配，波动率低者权重高。
        :param volatilities: 各策略年化波动率
        """
        n = len(strategies)
        if n == 0:
            return []
        if isinstance(volatilities, dict):
            vols = np.array([volatilities.get(s, 0.1) for s in strategies], dtype=float)
        else:
            vols = np.asarray(volatilities[:n], dtype=float)
        vols = np.where(vols <= 0, 1e-6, vols)
        inv_vol = 1.0 / vols
        if inv_vol.sum() <= 0:
            return [1.0 / n] * n
        w = inv_vol / inv_vol.sum()
        return w.tolist()
