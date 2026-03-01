# -*- coding: utf-8 -*-
"""
风控引擎：统一入口，仓位、回撤、单日亏损、VaR、集中度、熔断。私募级风控体系。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    from .position_limit import PositionLimit
    from .drawdown import DrawdownMonitor
except Exception:
    PositionLimit = None  # type: ignore
    DrawdownMonitor = None  # type: ignore
try:
    from .var_engine import check_var_breach
except Exception:
    check_var_breach = None  # type: ignore
try:
    from .concentration import ConcentrationLimit
except Exception:
    ConcentrationLimit = None  # type: ignore
try:
    from .circuit_breaker import CircuitBreaker
except Exception:
    CircuitBreaker = None  # type: ignore


class RiskEngine:
    """风控引擎：检查通过才允许下单或调仓；支持 VaR、集中度、熔断。"""

    def __init__(
        self,
        max_single_weight: float = 0.2,
        max_drawdown: float = 0.15,
        max_daily_loss_pct: float = 0.05,
        var_limit_pct: float = 0.03,
        max_top3_weight: float = 0.5,
    ):
        self.max_single_weight = max_single_weight
        self.max_drawdown = max_drawdown
        self.max_daily_loss_pct = max_daily_loss_pct
        self.var_limit_pct = var_limit_pct
        self._position_limit = PositionLimit(max_single_weight=max_single_weight) if PositionLimit else None
        self._drawdown = DrawdownMonitor(max_drawdown=max_drawdown) if DrawdownMonitor else None
        self._concentration = ConcentrationLimit(max_single_weight=max_single_weight, max_top3_weight=max_top3_weight) if ConcentrationLimit else None
        self._circuit = CircuitBreaker(max_daily_loss_pct=max_daily_loss_pct, max_drawdown=max_drawdown) if CircuitBreaker else None

    def check_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        positions: Dict[str, Dict[str, Any]],
        total_asset: float,
    ) -> tuple[bool, str]:
        """检查单笔订单是否通过风控。返回 (通过, 原因)。"""
        if self._position_limit:
            ok, msg = self._position_limit.check(symbol, qty, side, positions, total_asset)
            if not ok:
                return False, msg
        return True, "ok"

    def check_drawdown(self, equity_curve: List[float]) -> tuple[bool, str]:
        """检查当前回撤是否超限。"""
        if self._drawdown and equity_curve:
            ok, msg = self._drawdown.check(equity_curve)
            if not ok:
                return False, msg
        return True, "ok"

    def check_daily_loss(self, daily_pnl: float, total_asset: float) -> tuple[bool, str]:
        """单日亏损超限则熔断。"""
        if total_asset <= 0:
            return True, "ok"
        if daily_pnl / total_asset <= -self.max_daily_loss_pct:
            return False, f"单日亏损超限 {self.max_daily_loss_pct*100}%"
        return True, "ok"

    def check(self, orders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        生产级：过滤订单，仅保留 weight <= max_position 的订单。
        私募级：若启用熔断则先检查 is_tripped；集中度过滤。
        orders: [{"symbol", "qty", "side", "weight", ...}]
        返回: safe_orders
        """
        if self._circuit and self._circuit.is_tripped():
            return []
        safe = []
        for o in orders:
            w = float(o.get("weight", 0) or 0)
            if w <= self.max_single_weight:
                safe.append(o)
        if self._concentration:
            current_weights = {}
            safe = self._concentration.filter_orders(safe, current_weights)
        return safe

    def check_var(self, daily_pnl_pct: float) -> tuple[bool, str]:
        """VaR 熔断检查。"""
        if check_var_breach:
            return check_var_breach(daily_pnl_pct, self.var_limit_pct)
        return True, "ok"

    def trip_circuit(self) -> None:
        """主动熔断。"""
        if self._circuit:
            self._circuit.trip()

    def is_circuit_tripped(self) -> bool:
        return bool(self._circuit and self._circuit.is_tripped())
