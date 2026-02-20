# -*- coding: utf-8 -*-
"""
套利引擎：封装价差监控 + 多市场/多标的配置，统一输出信号供执行层下单。
"""
from typing import Optional, Callable, Dict, Any
from .spread_monitor import SpreadMonitor


class ArbEngine:
    """
    多市场套利引擎：可注册多对 (market_a, market_b) 或 (symbol_a, symbol_b)，
    每对一个 SpreadMonitor，统一 on_signal 汇总到执行/风控。
    """

    def __init__(self, on_signal: Optional[Callable[[str, str, Dict[str, Any]], None]] = None):
        self.on_signal = on_signal or self._default_signal
        self._monitors: Dict[str, SpreadMonitor] = {}

    @staticmethod
    def _default_signal(pair_id: str, side: str, info: Dict[str, Any]) -> None:
        print("ARB", pair_id, side, info.get("spread"))

    def add_pair(
        self,
        pair_id: str,
        upper: float,
        lower: float,
        use_zscore: bool = False,
        lookback: int = 20,
    ) -> SpreadMonitor:
        def _forward(side: str, info: Dict[str, Any]) -> None:
            self.on_signal(pair_id, side, info)

        mon = SpreadMonitor(upper=upper, lower=lower, on_signal=_forward, use_zscore=use_zscore, lookback=lookback)
        self._monitors[pair_id] = mon
        return mon

    def update(self, pair_id: str, price_a: float, price_b: float, asset_a: str = "A", asset_b: str = "B") -> None:
        if pair_id in self._monitors:
            self._monitors[pair_id].update(price_a, price_b, asset_a=asset_a, asset_b=asset_b)
