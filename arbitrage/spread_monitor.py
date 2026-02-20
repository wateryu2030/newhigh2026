# -*- coding: utf-8 -*-
"""
价差监控：维护多标的（或多市场）价格，计算价差与 Z-score，在突破上下轨时发出套利信号。
"""
from typing import Optional, Callable, Dict, Any, List


class SpreadMonitor:
    """
    监控 spread = price_a - price_b（或加权组合）。当 spread > upper 时发「做空 A 做多 B」；
    spread < lower 时发「做多 A 做空 B」。可选滚动均值/标准差做动态上下轨。
    """

    def __init__(
        self,
        upper: float,
        lower: float,
        on_signal: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        use_zscore: bool = False,
        lookback: int = 20,
    ):
        """
        :param upper: 价差上轨（或 Z 上轨）
        :param lower: 价差下轨（或 Z 下轨）
        :param on_signal: 信号回调 ("LONG_A_SHORT_B" | "SHORT_A_LONG_B", info)
        :param use_zscore: 若 True，用过去 lookback 的均值±标准差做动态轨
        :param lookback: Z-score 窗口
        """
        self.upper = upper
        self.lower = lower
        self.on_signal = on_signal or self._default_signal
        self.use_zscore = use_zscore
        self.lookback = lookback
        self._spread_history: List[float] = []
        self._last_signal: Optional[str] = None

    @staticmethod
    def _default_signal(side: str, info: Dict[str, Any]) -> None:
        print("ARB_SIGNAL", side, info.get("spread"), info.get("price_a"), info.get("price_b"))

    def update(self, price_a: float, price_b: float, asset_a: str = "A", asset_b: str = "B") -> None:
        """更新 A、B 价格，计算价差并判断是否触发信号。"""
        spread = price_a - price_b
        self._spread_history.append(spread)
        if len(self._spread_history) > self.lookback:
            self._spread_history.pop(0)
        info = {"spread": spread, "price_a": price_a, "price_b": price_b, "asset_a": asset_a, "asset_b": asset_b}
        if self.use_zscore and len(self._spread_history) >= self.lookback:
            import numpy as np
            arr = self._spread_history
            mu, std = np.mean(arr), np.std(arr) or 1e-12
            z = (spread - mu) / std
            if z >= self.upper:
                self._last_signal = "SHORT_A_LONG_B"
                self.on_signal(self._last_signal, {**info, "zscore": z})
            elif z <= self.lower:
                self._last_signal = "LONG_A_SHORT_B"
                self.on_signal(self._last_signal, {**info, "zscore": z})
        else:
            if spread >= self.upper:
                self._last_signal = "SHORT_A_LONG_B"
                self.on_signal(self._last_signal, info)
            elif spread <= self.lower:
                self._last_signal = "LONG_A_SHORT_B"
                self.on_signal(self._last_signal, info)

    def get_spread(self) -> float:
        return self._spread_history[-1] if self._spread_history else 0.0
