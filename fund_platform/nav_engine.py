# -*- coding: utf-8 -*-
"""
净值引擎：根据组合市值与总份额计算 NAV，支持申赎导致的份额变动。
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class NAVRecord:
    date: str
    nav: float
    aum: float
    total_units: float


class NAVEngine:
    """
    NAV = AUM / total_units。AUM 由外部按日更新（组合市值 + 现金）；
    total_units 随申购增加、赎回减少。
    """

    def __init__(self, initial_aum: float = 0.0, initial_units: float = 1.0):
        self.aum = initial_aum
        self.total_units = initial_units if initial_units > 0 else 1.0
        self._history: List[NAVRecord] = []

    def update_aum(self, aum: float, date: str = "") -> float:
        """更新 AUM 并返回当前 NAV。"""
        self.aum = aum
        nav = self.aum / self.total_units if self.total_units > 0 else 0.0
        if date:
            self._history.append(NAVRecord(date=date, nav=nav, aum=self.aum, total_units=self.total_units))
        return nav

    def add_units(self, units: float, date: str = "") -> float:
        """申购：增加份额（不改变 AUM，资金由 FundManager 计入）。返回新 NAV。"""
        self.total_units += max(0, units)
        return self.aum / self.total_units if self.total_units > 0 else 0.0

    def redeem_units(self, units: float, date: str = "") -> float:
        """赎回：减少份额。返回赎回前 NAV（用于计算赎回金额）。"""
        units = min(max(0, units), self.total_units)
        nav = self.aum / self.total_units if self.total_units > 0 else 0.0
        self.total_units -= units
        return nav

    def get_nav(self) -> float:
        return self.aum / self.total_units if self.total_units > 0 else 0.0

    def get_history(self) -> List[NAVRecord]:
        return list(self._history)
