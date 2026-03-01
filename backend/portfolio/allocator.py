# -*- coding: utf-8 -*-
"""
组合分配器：根据权重与总资金计算各标的目标仓位、可再平衡。
"""
from __future__ import annotations
from typing import Any, Dict, List


class PortfolioAllocator:
    """将权重与总资产转为各标的目标市值/股数。"""

    def __init__(self, total_asset: float = 1000000.0, max_single_weight: float = 0.2):
        self.total_asset = total_asset
        self.max_single_weight = max_single_weight

    def allocate(
        self,
        weights: Dict[str, float],
        prices: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        weights: {"600519": 0.2, "000001": 0.3, ...}
        prices: {"600519": 1800.0, "000001": 12.0, ...}
        返回: [{"code": "600519", "weight": 0.2, "target_value": 200000, "target_shares": 111}, ...]
        """
        out = []
        for code, w in weights.items():
            w = min(w, self.max_single_weight)
            price = float(prices.get(code, 0) or 0)
            if price <= 0:
                continue
            target_value = self.total_asset * w
            target_shares = int(target_value / price)
            out.append({
                "code": code,
                "weight": w,
                "target_value": target_value,
                "target_shares": target_shares,
                "price": price,
            })
        return out
