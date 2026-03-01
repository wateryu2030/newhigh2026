# -*- coding: utf-8 -*-
"""
熔断器：连续亏损、单日亏损、回撤超限时暂停交易。私募级风控。
"""
from __future__ import annotations
import time
from typing import List


class CircuitBreaker:
    """熔断：触发后在一段时间内禁止新开仓或全部禁止交易。"""

    def __init__(
        self,
        max_daily_loss_pct: float = 0.05,
        max_drawdown: float = 0.15,
        max_consecutive_loss_days: int = 3,
        cooldown_seconds: float = 86400.0,
    ):
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown = max_drawdown
        self.max_consecutive_loss_days = max_consecutive_loss_days
        self.cooldown_seconds = cooldown_seconds
        self._tripped_at: float | None = None
        self._consecutive_loss_days: int = 0

    def trip(self) -> None:
        self._tripped_at = time.time()

    def is_tripped(self) -> bool:
        if self._tripped_at is None:
            return False
        if time.time() - self._tripped_at >= self.cooldown_seconds:
            self._tripped_at = None
            return False
        return True

    def check_daily(self, daily_pnl_pct: float, total_asset: float) -> tuple[bool, str]:
        if total_asset <= 0:
            return True, "ok"
        if daily_pnl_pct <= -self.max_daily_loss_pct:
            self.trip()
            return False, f"熔断: 单日亏损 {daily_pnl_pct*100:.2f}%"
        return True, "ok"

    def check_drawdown(self, equity_curve: List[float]) -> tuple[bool, str]:
        if not equity_curve:
            return True, "ok"
        peak = equity_curve[0]
        for v in equity_curve:
            if v > peak:
                peak = v
        if peak <= 0:
            return True, "ok"
        dd = (peak - equity_curve[-1]) / peak
        if dd >= self.max_drawdown:
            self.trip()
            return False, f"熔断: 回撤 {dd*100:.1f}%"
        return True, "ok"

    def update_consecutive(self, daily_pnl: float) -> None:
        if daily_pnl < 0:
            self._consecutive_loss_days += 1
        else:
            self._consecutive_loss_days = 0
        if self._consecutive_loss_days >= self.max_consecutive_loss_days:
            self.trip()
