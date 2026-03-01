# -*- coding: utf-8 -*-
"""
PortfolioManager：基于 Broker 的资金与持仓视图，可计算总权益（需行情）。
"""
from __future__ import annotations
from typing import Any, Callable, Dict, Optional

from .broker import BrokerProtocol


class PortfolioManager:
    """
    组合管理：从 Broker 读取资金与持仓，提供 get_cash、get_positions、get_total_equity。
    不持有自有状态，仅作只读视图；资金与持仓由 SimBroker（或实盘 Broker）维护。
    """

    def __init__(self, broker: BrokerProtocol):
        self.broker = broker

    def get_cash(self) -> float:
        bal = self.broker.get_balance()
        return float(bal.get("cash", 0))

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        return self.broker.get_positions()

    def get_total_equity(self, get_price: Optional[Callable[[str], Optional[float]]] = None) -> float:
        """
        总权益 = 现金 + 持仓市值。
        若提供 get_price(symbol)，用其计算持仓市值；否则用 Broker 返回的 market_value 或 qty*avg_price。
        """
        bal = self.broker.get_balance()
        cash = float(bal.get("cash", 0))
        positions = self.broker.get_positions()
        if not get_price:
            mv = sum(
                p.get("market_value", p.get("qty", 0) * p.get("avg_price", 0))
                for p in positions.values()
            )
            return cash + float(mv)
        total_mv = 0.0
        for symbol, p in positions.items():
            qty = p.get("qty", 0)
            if qty <= 0:
                continue
            px = get_price(symbol)
            if px is not None:
                total_mv += qty * px
            else:
                total_mv += qty * p.get("avg_price", 0)
        return cash + total_mv
