# -*- coding: utf-8 -*-
"""
模拟券商：买卖执行、持仓更新、交易日志。
"""
from __future__ import annotations
from typing import List, Optional
from .account import Account, Position, TradeRecord


class PaperBroker:
    """
    模拟券商。
    - 初始资金 100 万（可配置）
    - buy(symbol, price, amount, date)
    - sell(symbol, price, amount, date)
    - 自动更新现金与持仓
    - 记录交易日志
    """

    def __init__(self, initial_cash: float = 1_000_000.0):
        self.account = Account(initial_cash=initial_cash)

    def buy(
        self,
        symbol: str,
        price: float,
        amount: int,
        date: str,
        reason: str = "",
    ) -> bool:
        """
        买入。
        :return: 是否成功
        """
        if amount <= 0 or price <= 0:
            return False
        total = price * amount
        if total > self.account.cash:
            return False
        self.account.cash -= total
        if symbol in self.account.positions:
            pos = self.account.positions[symbol]
            old_cost = pos.amount * pos.cost_price
            pos.amount += amount
            pos.cost_price = (old_cost + total) / pos.amount
            pos.current_price = price
        else:
            self.account.positions[symbol] = Position(
                symbol=symbol,
                amount=amount,
                cost_price=price,
                current_price=price,
            )
        rec = TradeRecord(
            date=date,
            symbol=symbol,
            side="BUY",
            price=price,
            amount=amount,
            total=total,
            reason=reason,
        )
        self.account.trades.append(rec)
        return True

    def sell(
        self,
        symbol: str,
        price: float,
        amount: int,
        date: str,
        reason: str = "",
    ) -> bool:
        """
        卖出。
        :return: 是否成功
        """
        if amount <= 0 or price <= 0:
            return False
        pos = self.account.positions.get(symbol)
        if pos is None or pos.amount < amount:
            return False
        total = price * amount
        self.account.cash += total
        pos.amount -= amount
        pos.current_price = price
        if pos.amount <= 0:
            del self.account.positions[symbol]
        rec = TradeRecord(
            date=date,
            symbol=symbol,
            side="SELL",
            price=price,
            amount=amount,
            total=total,
            reason=reason,
        )
        self.account.trades.append(rec)
        return True

    def sell_all(self, symbol: str, price: float, date: str, reason: str = "") -> bool:
        """清仓该标的。"""
        pos = self.account.positions.get(symbol)
        if pos is None:
            return False
        return self.sell(symbol, price, pos.amount, date, reason)

    def get_trades(self) -> List[TradeRecord]:
        return self.account.trades.copy()
