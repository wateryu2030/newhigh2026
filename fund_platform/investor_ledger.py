# -*- coding: utf-8 -*-
"""
投资者台账：记录每位投资者的份额、申购/赎回流水。
"""
from typing import Dict, List, Any
from dataclasses import dataclass, field


@dataclass
class CashFlow:
    investor_id: str
    type: str  # "subscribe" | "redeem"
    amount: float
    units: float
    nav: float
    date: str


class InvestorLedger:
    """
    投资者维度：investor_id -> 当前份额；流水列表供对账与报表。
    """

    def __init__(self):
        self.units: Dict[str, float] = {}
        self.cash_flows: List[CashFlow] = []

    def subscribe(self, investor_id: str, amount: float, nav: float, date: str = "") -> float:
        """申购：金额/NAV 得到份额，计入投资者并记流水。"""
        if nav <= 0:
            return 0.0
        units = amount / nav
        self.units[investor_id] = self.units.get(investor_id, 0.0) + units
        self.cash_flows.append(CashFlow(investor_id=investor_id, type="subscribe", amount=amount, units=units, nav=nav, date=date))
        return units

    def redeem(self, investor_id: str, units: float, nav: float, date: str = "") -> float:
        """赎回：份额 × NAV = 金额，扣减份额并记流水。"""
        held = self.units.get(investor_id, 0.0)
        units = min(units, held)
        amount = units * nav
        self.units[investor_id] = held - units
        self.cash_flows.append(CashFlow(investor_id=investor_id, type="redeem", amount=amount, units=units, nav=nav, date=date))
        return amount

    def get_units(self, investor_id: str) -> float:
        return self.units.get(investor_id, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {"units_by_investor": dict(self.units), "cash_flows_count": len(self.cash_flows)}
