# -*- coding: utf-8 -*-
"""
订单路由：将目标分配转为可执行订单列表（可对接经纪商或模拟）。
"""
from __future__ import annotations
from typing import Any, Dict, List


class OrderRouter:
    def route(self, allocation: Dict[str, float], current_positions: Dict[str, float] = None) -> List[Dict[str, Any]]:
        """根据目标 allocation 与当前持仓生成订单列表。"""
        current_positions = current_positions or {}
        orders = []
        for name, target_value in allocation.items():
            current = current_positions.get(name, 0.0)
            delta = target_value - current
            if abs(delta) < 1e-6:
                continue
            orders.append({
                "strategy": name,
                "target_value": target_value,
                "current_value": current,
                "delta": delta,
                "side": "BUY" if delta > 0 else "SELL",
            })
        return orders
