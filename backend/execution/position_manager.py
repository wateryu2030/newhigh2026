# -*- coding: utf-8 -*-
"""
持仓管理：从 BrokerAPI 获取持仓，提供市值、权重、成本等视图。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .broker_api import BrokerAPI


class PositionManager:
    def __init__(self, broker: Optional[BrokerAPI] = None):
        self.broker = broker or BrokerAPI(mode="simulation")

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        return self.broker.get_positions()

    def get_position_weights(self, total_asset: float) -> Dict[str, float]:
        """返回 symbol -> 权重 (0~1)。"""
        if total_asset <= 0:
            return {}
        pos = self.broker.get_positions()
        return {
            sym: (p.get("market_value", 0) or p.get("qty", 0) * p.get("avg_price", 0)) / total_asset
            for sym, p in pos.items()
        }

    def get_position_list(self) -> List[Dict[str, Any]]:
        """返回列表形态，便于写库与展示。"""
        pos = self.broker.get_positions()
        return [
            {"symbol": sym, "qty": p.get("qty", 0), "avg_price": p.get("avg_price", 0), "market_value": p.get("market_value", 0)}
            for sym, p in pos.items()
        ]
