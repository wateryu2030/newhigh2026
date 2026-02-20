# -*- coding: utf-8 -*-
"""
投资组合管理：按标的维护持仓市值，汇总总资产。
可与实盘/模拟盘对接，供 monitor API 使用。
"""
from typing import Dict, Optional, Any


class PortfolioManager:
    """
    组合管理器：维护 code -> 持仓价值（或股数×价格），并计算总资产。
    """

    def __init__(self, capital: float = 0.0):
        self.capital = capital
        self.positions: Dict[str, float] = {}  # code -> 市值或数量

    def update(self, code: str, value: float) -> None:
        """更新某标的持仓价值（或数量）。"""
        self.positions[code] = value

    def get(self, code: str) -> float:
        """获取某标的持仓价值。"""
        return self.positions.get(code, 0.0)

    def total_value(self) -> float:
        """总资产 = 现金 + 所有持仓市值。"""
        return self.capital + sum(self.positions.values())

    def position_sum(self) -> float:
        """仅持仓市值之和。"""
        return sum(self.positions.values())

    def to_dict(self) -> Dict[str, Any]:
        """供 API 序列化：现金、持仓、总资产。"""
        return {
            "cash": self.capital,
            "positions": dict(self.positions),
            "total_value": self.total_value(),
        }
