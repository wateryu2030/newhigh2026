# -*- coding: utf-8 -*-
"""
集中度限制：单标的、单行业、组合前 N 占比上限。私募级风控。
"""
from __future__ import annotations
from typing import Any, Dict, List


class ConcentrationLimit:
    """单标的、前 N 大持仓占比上限。"""

    def __init__(
        self,
        max_single_weight: float = 0.2,
        max_top3_weight: float = 0.5,
        max_top10_weight: float = 0.8,
    ):
        self.max_single_weight = max_single_weight
        self.max_top3_weight = max_top3_weight
        self.max_top10_weight = max_top10_weight

    def check_weights(self, weights: Dict[str, float]) -> tuple[bool, str]:
        """检查权重是否满足集中度。"""
        if not weights:
            return True, "ok"
        w = sorted(weights.values(), reverse=True)
        if w[0] > self.max_single_weight:
            return False, f"单标的权重 {w[0]*100:.1f}% 超过 {self.max_single_weight*100}%"
        if len(w) >= 3 and sum(w[:3]) > self.max_top3_weight:
            return False, f"前3集中度 {sum(w[:3])*100:.1f}% 超过 {self.max_top3_weight*100}%"
        if len(w) >= 10 and sum(w[:10]) > self.max_top10_weight:
            return False, f"前10集中度 {sum(w[:10])*100:.1f}% 超过 {self.max_top10_weight*100}%"
        return True, "ok"

    def filter_orders(
        self,
        orders: List[Dict[str, Any]],
        current_weights: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """过滤订单使执行后仍满足集中度。简化：仅按单笔 weight 过滤。"""
        out = []
        for o in orders:
            w = float(o.get("weight", 0) or 0)
            if w <= self.max_single_weight:
                out.append(o)
        return out
