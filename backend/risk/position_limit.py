# -*- coding: utf-8 -*-
"""
仓位限制：单标的、组合权重上限。
"""
from __future__ import annotations
from typing import Any, Dict


class PositionLimit:
    """单标的权重不超过 max_single_weight。"""

    def __init__(self, max_single_weight: float = 0.2):
        self.max_single_weight = max_single_weight

    def check(
        self,
        symbol: str,
        qty: float,
        side: str,
        positions: Dict[str, Dict[str, Any]],
        total_asset: float,
    ) -> tuple[bool, str]:
        """
        检查下单后是否超过单标的权重上限。
        positions: { symbol: { "qty", "cost" 或 "market_value" } }
        """
        if total_asset <= 0:
            return True, "ok"
        if side.upper() != "BUY":
            return True, "ok"
        # 简化：仅用 qty * 当前价估算；实际应传入 price
        pos = positions.get(symbol, {})
        current_value = float(pos.get("market_value", 0) or pos.get("cost", 0) or 0)
        # 假设新买金额与 current_value 同量级估算，这里仅做示意
        if current_value / total_asset >= self.max_single_weight and qty > 0:
            return False, f"单标的权重已达上限 {self.max_single_weight*100}%"
        return True, "ok"
