# -*- coding: utf-8 -*-
"""
回撤监控：超过 max_drawdown 可熔断或告警。
"""
from __future__ import annotations
from typing import List


class DrawdownMonitor:
    """回撤超过阈值返回不通过。"""

    def __init__(self, max_drawdown: float = 0.15):
        self.max_drawdown = max_drawdown

    def check(self, equity_curve: List[float]) -> tuple[bool, str]:
        """
        equity_curve: 净值序列（从旧到新）。
        当前回撤 = (峰值 - 当前) / 峰值，超过 max_drawdown 返回 False。
        """
        if not equity_curve:
            return True, "ok"
        peak = equity_curve[0]
        current = equity_curve[-1]
        for v in equity_curve:
            if v > peak:
                peak = v
        if peak <= 0:
            return True, "ok"
        dd = (peak - current) / peak
        if dd >= self.max_drawdown:
            return False, f"回撤超限 {dd*100:.1f}% >= {self.max_drawdown*100}%"
        return True, "ok"
