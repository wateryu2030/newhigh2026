# -*- coding: utf-8 -*-
"""
券商模拟器：T+1、滑点 0.1%、手续费 0.03%、涨跌停限制。
"""
from __future__ import annotations
from typing import Dict, List, Optional
import pandas as pd


class BrokerSimulator:
    """
    A 股交易规则模拟。
    - T+1：当日买入下一日可卖
    - 滑点：0.1%（可配置）
    - 手续费：0.03%（佣金，可配置）
    - 涨跌停：±10%（科创板/创业板等可子类覆盖）
    """

    def __init__(
        self,
        slippage_pct: float = 0.001,
        commission_pct: float = 0.0003,
        limit_up_pct: float = 0.10,
        limit_down_pct: float = -0.10,
    ):
        self.slippage_pct = slippage_pct
        self.commission_pct = commission_pct
        self.limit_up_pct = limit_up_pct
        self.limit_down_pct = limit_down_pct

    def apply_slippage(self, price: float, side: str = "BUY") -> float:
        """应用滑点：买入加价、卖出减价。"""
        if side.upper() == "BUY":
            return price * (1 + self.slippage_pct)
        return price * (1 - self.slippage_pct)

    def apply_commission(self, value: float) -> float:
        """手续费（按成交金额）。"""
        return value * self.commission_pct

    def can_trade(
        self,
        symbol: str,
        price: float,
        prev_close: float,
        side: str,
    ) -> bool:
        """是否在涨跌停内可成交。"""
        if prev_close <= 0:
            return True
        pct = (price - prev_close) / prev_close
        if side.upper() == "BUY":
            return pct < self.limit_up_pct
        return pct > self.limit_down_pct

    def fill_orders(
        self,
        orders: List[Dict],
        prices: Dict[str, float],
        prev_closes: Optional[Dict[str, float]] = None,
    ) -> List[Dict]:
        """
        模拟成交：应用滑点与手续费，过滤涨跌停无法成交的订单。
        :param orders: [ {"symbol": s, "value": v, "side": "BUY"}, ... ]
        :param prices: 当前/委托价 { symbol: price }
        :param prev_closes: 前收 { symbol: prev_close }，缺省则不检查涨跌停
        :return: [ {"symbol", "value", "side", "fill_price", "commission", "filled": True/False}, ... ]
        """
        prev_closes = prev_closes or {}
        out = []
        for o in orders:
            sym = o.get("symbol", "")
            value = float(o.get("value", 0))
            side = (o.get("side") or "BUY").upper()
            price = prices.get(sym, 0)
            if price <= 0 or value <= 0:
                out.append({**o, "fill_price": 0, "commission": 0, "filled": False})
                continue
            prev = prev_closes.get(sym, price)
            if not self.can_trade(sym, price, prev, side):
                out.append({**o, "fill_price": price, "commission": 0, "filled": False})
                continue
            fill_price = self.apply_slippage(price, side)
            commission = self.apply_commission(value)
            out.append({
                **o,
                "fill_price": fill_price,
                "commission": commission,
                "filled": True,
            })
        return out
