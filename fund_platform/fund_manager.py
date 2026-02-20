# -*- coding: utf-8 -*-
"""
基金管理人：统一 NAV、投资者台账、申赎处理与 AUM 更新，对外提供申购/赎回/查询接口。
"""
from typing import Dict, Any, Optional
from .nav_engine import NAVEngine
from .investor_ledger import InvestorLedger


class FundManager:
    """
    整合 NAV 引擎与投资者台账：申购时资金进入 AUM、增加总份额与投资者份额；
    赎回时按 NAV 计算金额、减少份额并可从 AUM 扣减（实际资金划转由执行层做）。
    """

    def __init__(self, initial_capital: float = 0.0):
        self.nav_engine = NAVEngine(initial_aum=initial_capital, initial_units=1.0)
        self.ledger = InvestorLedger()
        self._initial_units = 1.0
        self.nav_engine.total_units = self._initial_units

    def update_aum(self, aum: float, date: str = "") -> float:
        """更新组合总资产，返回当前 NAV。"""
        return self.nav_engine.update_aum(aum, date=date)

    def subscribe(self, investor_id: str, amount: float, date: str = "") -> Dict[str, Any]:
        """
        申购：按当前 NAV 计算份额，增加 AUM 与总份额、投资者份额。
        :return: {"units": float, "nav": float, "amount": float}
        """
        nav = self.nav_engine.get_nav()
        units = self.ledger.subscribe(investor_id, amount, nav, date=date)
        self.nav_engine.aum += amount
        self.nav_engine.total_units += units
        return {"units": units, "nav": nav, "amount": amount}

    def redeem(self, investor_id: str, units: float, date: str = "") -> Dict[str, Any]:
        """
        赎回：按当前 NAV 计算金额，扣减份额与 AUM。
        :return: {"amount": float, "nav": float, "units": float}
        """
        nav = self.nav_engine.get_nav()
        amount = units * nav
        self.ledger.redeem(investor_id, units, nav, date=date)
        self.nav_engine.total_units -= units
        self.nav_engine.aum -= amount
        return {"amount": amount, "nav": nav, "units": units}

    def get_nav(self) -> float:
        return self.nav_engine.get_nav()

    def get_aum(self) -> float:
        return self.nav_engine.aum

    def get_investor_units(self, investor_id: str) -> float:
        return self.ledger.get_units(investor_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nav": self.get_nav(),
            "aum": self.get_aum(),
            "total_units": self.nav_engine.total_units,
            "ledger": self.ledger.to_dict(),
        }
