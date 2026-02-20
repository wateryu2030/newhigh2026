# -*- coding: utf-8 -*-
"""
Tick 级高频策略引擎：接收 tick 流，产生买卖信号并触发下单。
架构：行情流 → 信号引擎 → 下单引擎 → 风控。
"""
from typing import Callable, Optional, Any, Dict


class TickEngine:
    """
    接收 on_tick(tick)，内部维护 last_price 等状态，满足条件时调用 buy/sell 回调。
    tick 建议格式：{"price": float, "volume": int, "time": ..., "bid": ..., "ask": ...}
    """

    def __init__(
        self,
        on_buy: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_sell: Optional[Callable[[Dict[str, Any]], None]] = None,
        threshold_up: float = 0.001,
        threshold_down: float = -0.001,
    ):
        self.last_price: Optional[float] = None
        self.on_buy = on_buy or self._default_buy
        self.on_sell = on_sell or self._default_sell
        self.threshold_up = threshold_up
        self.threshold_down = threshold_down

    @staticmethod
    def _default_buy(tick: Dict[str, Any]) -> None:
        print("BUY ORDER", tick.get("price"), tick.get("time"))

    @staticmethod
    def _default_sell(tick: Dict[str, Any]) -> None:
        print("SELL ORDER", tick.get("price"), tick.get("time"))

    def on_tick(self, tick: Dict[str, Any]) -> None:
        price = tick.get("price")
        if price is None:
            return
        if self.last_price is not None:
            ret = (price - self.last_price) / (self.last_price or 1e-12)
            if ret >= self.threshold_up:
                self.on_buy(tick)
            elif ret <= self.threshold_down:
                self.on_sell(tick)
        self.last_price = price

    def buy(self, tick: Optional[Dict[str, Any]] = None) -> None:
        self.on_buy(tick or {"price": self.last_price})
