# -*- coding: utf-8 -*-
"""
策略池：管理多策略（趋势 / AI / 均值回归 / 突破等），统一 run 返回各策略结果。
可与 PortfolioEngine、CapitalAllocator 配合实现多策略组合与资金分配。
"""
from typing import List, Callable, Any, Dict


class StrategyPool:
    """
    策略池：注册多个策略（可调用对象），run() 时依次执行并返回结果列表。
    策略可为 generate_signals(df) 风格，或任意 callable。
    """

    def __init__(self):
        self.strategies: List[Callable[..., Any]] = []

    def add(self, strategy: Callable[..., Any]) -> "StrategyPool":
        self.strategies.append(strategy)
        return self

    def run(self, *args, **kwargs) -> List[Any]:
        """执行所有策略，返回各策略结果列表。"""
        results = []
        for s in self.strategies:
            try:
                out = s(*args, **kwargs)
                results.append(out)
            except Exception as e:
                results.append({"error": str(e)})
        return results

    def __len__(self) -> int:
        return len(self.strategies)
