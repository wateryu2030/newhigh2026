# -*- coding: utf-8 -*-
"""
模拟交易账户：资产、持仓、现金、收益率、最大回撤。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime


@dataclass
class Position:
    """单只股票持仓。"""
    symbol: str
    amount: int
    cost_price: float
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        p = self.current_price if self.current_price > 0 else self.cost_price
        return self.amount * p

    @property
    def cost_value(self) -> float:
        return self.amount * self.cost_price

    @property
    def profit_ratio(self) -> float:
        if self.cost_value == 0:
            return 0.0
        return (self.market_value - self.cost_value) / self.cost_value


@dataclass
class TradeRecord:
    """单笔交易记录。"""
    date: str
    symbol: str
    side: str  # BUY | SELL
    price: float
    amount: int
    total: float
    reason: str = ""


class Account:
    """
    模拟交易账户。
    - 总资产 = 现金 + 持仓市值
    - 收益率 = (当前总资产 - 初始资金) / 初始资金
    - 最大回撤 = 从高点到低点的最大跌幅
    """

    def __init__(self, initial_cash: float = 1_000_000.0):
        self.initial_cash: float = initial_cash
        self.cash: float = initial_cash
        self.positions: Dict[str, Position] = {}
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[tuple] = []  # (date_str, total_equity)
        self.peak_equity: float = initial_cash

    @property
    def position_value(self) -> float:
        """持仓总市值。"""
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_equity(self) -> float:
        """当前总资产。"""
        return self.cash + self.position_value

    @property
    def profit_ratio(self) -> float:
        """当前收益率（小数）。"""
        if self.initial_cash == 0:
            return 0.0
        return (self.total_equity - self.initial_cash) / self.initial_cash

    @property
    def max_drawdown(self) -> float:
        """最大回撤（小数，如 0.15 表示 15%）。"""
        if not self.equity_curve or self.peak_equity <= 0:
            return 0.0
        max_dd = 0.0
        peak = self.peak_equity
        for _, eq in self.equity_curve:
            if eq > peak:
                peak = eq
            if peak > 0:
                dd = (peak - eq) / peak
                if dd > max_dd:
                    max_dd = dd
        return max_dd

    def update_position_price(self, symbol: str, price: float) -> None:
        """更新持仓当前价（用于市值计算）。"""
        if symbol in self.positions:
            self.positions[symbol].current_price = price

    def record_equity(self, date_str: str) -> None:
        """记录当日权益。"""
        eq = self.total_equity
        self.equity_curve.append((date_str, eq))
        if eq > self.peak_equity:
            self.peak_equity = eq
