# -*- coding: utf-8 -*-
"""
风险预算引擎：市场状态决定总仓位；单股风险 = capital * risk_per_trade / stop_loss_distance。
"""
from __future__ import annotations
from typing import Literal

RegimeType = Literal["bull", "bear", "sideways", "high_volatility"]

# 市场状态 → 总仓位上限（0~1）
REGIME_POSITION_LIMIT: dict[str, float] = {
    "bull": 0.80,
    "sideways": 0.50,
    "bear": 0.20,
    "high_volatility": 0.30,
}


def get_position_limit(regime: RegimeType) -> float:
    """根据市场状态返回总仓位上限。"""
    return REGIME_POSITION_LIMIT.get(regime, 0.5)


def position_size_by_risk(
    capital: float,
    risk_per_trade: float,
    stop_loss_distance: float,
    price: float,
) -> int:
    """
    按风险预算计算单笔仓位股数（整百）。
    position_size = capital * risk_per_trade / stop_loss_distance
    stop_loss_distance: 每股止损距离（元）或比例换算成金额。
    """
    if capital <= 0 or price <= 0 or stop_loss_distance <= 0:
        return 0
    value = capital * risk_per_trade / (stop_loss_distance / price)
    qty = int(value / price) // 100 * 100
    return max(0, qty)


def apply_regime_cap(total_asset: float, target_value: float, regime: RegimeType) -> float:
    """在目标市值上施加市场状态仓位上限。"""
    cap = get_position_limit(regime)
    max_value = total_asset * cap
    return min(target_value, max_value)
