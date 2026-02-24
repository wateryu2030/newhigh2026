# -*- coding: utf-8 -*-
"""
风控系统：单股止损 8%、组合最大回撤 12%、单日亏损限制 3%、黑名单过滤。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Set

STOP_LOSS_SINGLE = 0.08
MAX_DRAWDOWN = 0.12
MAX_DAILY_LOSS = 0.03


class RiskController:
    def __init__(
        self,
        stop_loss_single: float = STOP_LOSS_SINGLE,
        max_drawdown: float = MAX_DRAWDOWN,
        max_daily_loss: float = MAX_DAILY_LOSS,
        blacklist: Optional[Set[str]] = None,
    ):
        self.stop_loss_single = stop_loss_single
        self.max_drawdown = max_drawdown
        self.max_daily_loss = max_daily_loss
        self.blacklist = blacklist or set()

    def filter_blacklist(self, symbols: List[str]) -> List[str]:
        """过滤黑名单标的。"""
        if not self.blacklist:
            return list(symbols)
        return [s for s in symbols if s not in self.blacklist]

    def check_single_stop(self, symbol: str, cost: float, current_price: float) -> bool:
        """单股止损：当前亏损超过 8% 返回 True（应平仓）。"""
        if cost <= 0:
            return False
        pnl_pct = (current_price - cost) / cost
        return pnl_pct <= -self.stop_loss_single

    def check_drawdown(self, total_asset: float, peak_asset: float) -> bool:
        """组合回撤超 12% 返回 True（应减仓/暂停）。"""
        if peak_asset <= 0:
            return False
        dd = (peak_asset - total_asset) / peak_asset
        return dd >= self.max_drawdown

    def check_daily_loss(self, total_asset: float, daily_pnl: float) -> bool:
        """单日亏损超 3% 返回 True（应暂停开仓）。"""
        if total_asset <= 0:
            return False
        return daily_pnl < 0 and (-daily_pnl / total_asset) >= self.max_daily_loss

    def approve_trade(
        self,
        symbol: str,
        side: str,
        portfolio: Dict,
        position_cost: Optional[float] = None,
        current_price: Optional[float] = None,
    ) -> tuple[bool, str]:
        """
        综合风控：黑名单、单股止损、回撤、单日亏损。
        返回 (是否允许, 原因)。
        """
        if symbol in self.blacklist:
            return False, "黑名单"
        total = float(portfolio.get("total_asset") or 0)
        peak = float(portfolio.get("peak_asset") or total)
        daily_pnl = float(portfolio.get("daily_pnl") or 0)
        if self.check_drawdown(total, peak):
            return False, "组合回撤超限"
        if self.check_daily_loss(total, daily_pnl) and side == "BUY":
            return False, "单日亏损超限"
        if side == "SELL" and position_cost is not None and current_price is not None:
            if self.check_single_stop(symbol, position_cost, current_price):
                return True, "触发单股止损"
        return True, "通过"
