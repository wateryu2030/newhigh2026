# -*- coding: utf-8 -*-
"""
基金经理主引擎：拉取策略与指标 → AI 分配权重 → 风险控制 → 输出再平衡结果。
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional

from .strategy_layer.strategy_registry import StrategyRegistry
from .ai_layer.ai_allocator import AIAllocator
from .capital_layer.capital_allocator import CapitalAllocator
from .risk_layer.drawdown_control import DrawdownControl
from .execution_layer.order_router import OrderRouter


class FundManager:
    def __init__(
        self,
        registry: StrategyRegistry,
        allocator: AIAllocator,
        capital_allocator: Optional[CapitalAllocator] = None,
        drawdown_control: Optional[DrawdownControl] = None,
        order_router: Optional[OrderRouter] = None,
        capital: float = 1_000_000,
    ):
        self.registry = registry
        self.allocator = allocator
        self.capital_allocator = capital_allocator or CapitalAllocator()
        self.drawdown_control = drawdown_control or DrawdownControl()
        self.order_router = order_router or OrderRouter()
        self.capital = capital

    def rebalance(
        self,
        current_max_drawdown: float = 0.0,
        current_positions: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        再平衡：取各策略指标 → AI 分配权重 → 回撤缩放 → 资金分配 → 订单列表。
        """
        strategies = self.registry.get_all()
        if not strategies:
            return {"allocation": {}, "orders": [], "risk_scale": 1.0, "regime": "unknown"}
        names = []
        metrics = []
        for name, s in strategies.items():
            m = s.get("metrics") or {}
            names.append(name)
            metrics.append(m)
        weights = self.allocator.allocate(metrics)
        if len(weights) != len(names):
            return {"allocation": {}, "orders": [], "risk_scale": 1.0}
        risk_scale = self.drawdown_control.scale_for_drawdown(current_max_drawdown)
        weights = weights * risk_scale
        if weights.sum() > 1e-12:
            weights = weights / weights.sum()
        allocation = self.capital_allocator.allocate(self.capital * risk_scale, weights, names)
        orders = self.order_router.route(allocation, current_positions)
        return {
            "allocation": allocation,
            "orders": orders,
            "risk_scale": risk_scale,
            "weights": dict(zip(names, weights.tolist())),
        }
