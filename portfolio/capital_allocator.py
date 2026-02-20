# -*- coding: utf-8 -*-
"""
资金分配器：机构核心算法 — 等权 / 风险平价 / 夏普最大化等。
当前实现等权分配；后续可扩展 risk_parity、max_sharpe。
"""
from typing import List, Dict, Any, Union


class CapitalAllocator:
    """
    根据策略列表与总资金，分配各策略资金。
    策略可用 id/name 标识，或直接用策略对象（需可哈希或转 str）。
    """

    def allocate(
        self,
        capital: float,
        strategies: List[Any],
        weights: Union[List[float], None] = None,
    ) -> Dict[Any, float]:
        """
        :param capital: 总资金
        :param strategies: 策略列表（或策略 id 列表）
        :param weights: 各策略权重，长度需与 strategies 一致；None 表示等权
        :return: { strategy: allocated_capital }
        """
        n = len(strategies)
        if n == 0:
            return {}
        if weights is None or len(weights) != n:
            alloc_each = capital / n
            return {s: alloc_each for s in strategies}
        total_w = sum(weights)
        if total_w <= 0:
            alloc_each = capital / n
            return {s: alloc_each for s in strategies}
        return {
            s: capital * (w / total_w)
            for s, w in zip(strategies, weights)
        }
