# -*- coding: utf-8 -*-
"""
回撤控制：最大回撤>15%降仓、连续亏损风险模式、波动率异常停交易。
"""
from __future__ import annotations
from typing import Union
import numpy as np


class DrawdownControl:
    def __init__(
        self,
        max_drawdown_warn: float = 0.15,
        max_drawdown_stop: float = 0.20,
        consecutive_loss_days: int = 3,
        vol_spike_ratio: float = 2.0,
    ):
        self.max_drawdown_warn = max_drawdown_warn
        self.max_drawdown_stop = max_drawdown_stop
        self.consecutive_loss_days = consecutive_loss_days
        self.vol_spike_ratio = vol_spike_ratio

    def scale_for_drawdown(self, current_max_dd: float) -> float:
        """根据当前最大回撤返回仓位缩放 [0,1]。"""
        if current_max_dd >= self.max_drawdown_stop:
            return 0.0
        if current_max_dd >= self.max_drawdown_warn:
            return max(0.0, 1.0 - (current_max_dd - self.max_drawdown_warn) / (self.max_drawdown_stop - self.max_drawdown_warn))
        return 1.0

    def risk_mode_for_consecutive_losses(self, recent_returns: list) -> bool:
        """连续 N 天亏损则进入风险模式。"""
        if len(recent_returns) < self.consecutive_loss_days:
            return False
        tail = recent_returns[-self.consecutive_loss_days:]
        return all(r < 0 for r in tail)

    def vol_anomaly(self, current_vol: float, baseline_vol: float) -> bool:
        """波动率异常（当前/基准 > ratio）则建议停止交易。"""
        if baseline_vol <= 0:
            return False
        return (current_vol / baseline_vol) >= self.vol_spike_ratio
