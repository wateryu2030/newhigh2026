# -*- coding: utf-8 -*-
"""
风险控制模块：单票仓位上限、单日亏损上限、最大回撤限制，信号与组合层面的风险检查。
"""
from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

# 单只股票最大仓位占比（占净资产）
max_position_per_stock = 0.2
# 单日最大亏损比例（触发后停止开新仓/减仓）
max_daily_loss = 0.05
# 最大回撤比例（从权益高点算）
max_drawdown = 0.15


def check_risk(signal: Dict[str, Any], portfolio: Dict[str, Any]) -> Tuple[bool, str]:
    """
    检查当前信号在给定组合下是否通过风险控制。
    signal: {"symbol": "000001", "action": "BUY", "confidence": 0.82, ...}
    portfolio: {"total_asset": float, "cash": float, "positions": {symbol: {"market_value": float, "weight": float}}, "daily_pnl": float, "peak_asset": float}
    返回: (是否通过, 原因说明)
    """
    if not signal or not portfolio:
        return False, "缺少 signal 或 portfolio"
    action = (signal.get("action") or "").upper()
    symbol = (signal.get("symbol") or "").strip()
    if not symbol or action not in ("BUY", "SELL"):
        return True, "非买卖信号，跳过"

    total = float(portfolio.get("total_asset") or 0)
    if total <= 0:
        return False, "总资产无效"
    daily_pnl = float(portfolio.get("daily_pnl") or 0)
    peak_asset = float(portfolio.get("peak_asset") or total)
    positions = portfolio.get("positions") or {}

    if peak_asset > 0 and total < peak_asset * (1 - max_drawdown):
        return False, f"已达最大回撤限制 {max_drawdown:.1%}，暂停开仓"
    if daily_pnl < 0 and total > 0 and (-daily_pnl / total) >= max_daily_loss:
        return False, f"单日亏损已达上限 {max_daily_loss:.1%}，暂停开仓"

    if action == "BUY":
        current_weight = float(
            (positions.get(symbol) or positions.get(symbol + ".XSHE") or positions.get(symbol + ".XSHG") or {}).get("weight") or 0
        )
        if current_weight >= max_position_per_stock:
            return False, f"单票仓位已达上限 {max_position_per_stock:.1%}"
        total_in_stocks = sum(float((p or {}).get("market_value") or 0) for p in positions.values())
        if total_in_stocks + (total * max_position_per_stock) > total * (1 + 0.01):
            pass
    return True, "通过"


class RiskManager:
    """风险管理器：封装阈值与检查逻辑，便于配置与扩展。"""

    def __init__(
        self,
        max_position_per_stock: float = 0.2,
        max_daily_loss: float = 0.05,
        max_drawdown: float = 0.15,
    ):
        self.max_position_per_stock = max_position_per_stock
        self.max_daily_loss = max_daily_loss
        self.max_drawdown = max_drawdown

    def check_risk(self, signal: Dict[str, Any], portfolio: Dict[str, Any]) -> Tuple[bool, str]:
        """与模块级 check_risk 一致，使用实例阈值。"""
        if not signal or not portfolio:
            return False, "缺少 signal 或 portfolio"
        action = (signal.get("action") or "").upper()
        symbol = (signal.get("symbol") or "").strip()
        if not symbol or action not in ("BUY", "SELL"):
            return True, "跳过"
        total = float(portfolio.get("total_asset") or 0)
        if total <= 0:
            return False, "总资产无效"
        daily_pnl = float(portfolio.get("daily_pnl") or 0)
        peak_asset = float(portfolio.get("peak_asset") or total)
        positions = portfolio.get("positions") or {}
        if peak_asset > 0 and total < peak_asset * (1 - self.max_drawdown):
            return False, f"已达最大回撤 {self.max_drawdown:.1%}"
        if daily_pnl < 0 and (-daily_pnl / total) >= self.max_daily_loss:
            return False, f"单日亏损达上限 {self.max_daily_loss:.1%}"
        if action == "BUY":
            current_weight = float(
                (positions.get(symbol) or positions.get(symbol + ".XSHE") or positions.get(symbol + ".XSHG") or {}).get("weight") or 0
            )
            if current_weight >= self.max_position_per_stock:
                return False, f"单票仓位已达上限 {self.max_position_per_stock:.1%}"
        return True, "通过"
