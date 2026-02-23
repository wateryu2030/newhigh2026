# -*- coding: utf-8 -*-
"""
风险预算仓位：单笔风险 = 账户×风险比例，仓位 = 单笔风险/止损幅度。
职业系统标准公式。
"""
from __future__ import annotations
from typing import Optional, Tuple


def position_size(
    capital: float,
    risk_pct: float = 0.01,
    stop_loss_pct: float = 0.05,
    max_position_pct: float = 0.20,
) -> Tuple[float, float]:
    """
    风险预算仓位。
    :param capital: 总资金
    :param risk_pct: 单笔愿意承担的风险比例（如 1%）
    :param stop_loss_pct: 止损幅度（如 5%）
    :param max_position_pct: 单股最大仓位上限（如 20%）
    :return: (建议仓位金额, 建议仓位比例 0~max_position_pct)
    """
    if capital <= 0 or stop_loss_pct <= 0:
        return 0.0, 0.0
    risk_amount = capital * risk_pct
    size = risk_amount / stop_loss_pct
    ratio = size / capital
    ratio = min(ratio, max_position_pct)
    size = capital * ratio
    return round(size, 2), round(ratio, 4)


def position_size_with_atr(
    capital: float,
    atr: float,
    current_price: float,
    atr_mult: float = 2.0,
    risk_pct: float = 0.01,
    max_position_pct: float = 0.20,
) -> Tuple[float, int]:
    """
    基于 ATR 的止损与仓位：止损距离 = atr * atr_mult（元），股数 = 风险金额/止损距离。
    :param capital: 总资金
    :param atr: 当前 ATR（元）
    :param current_price: 当前价（用于算金额与股数）
    :param atr_mult: 止损倍数
    :param risk_pct: 单笔风险比例
    :param max_position_pct: 单股最大仓位
    :return: (建议仓位金额, 建议股数)
    """
    if capital <= 0 or atr <= 0 or current_price <= 0:
        return 0.0, 0
    risk_amount = capital * risk_pct
    stop_distance = atr * atr_mult
    if stop_distance <= 0:
        return 0.0, 0
    shares = int(risk_amount / stop_distance)
    amount = shares * current_price
    max_amount = capital * max_position_pct
    if amount > max_amount:
        amount = max_amount
        shares = int(amount / current_price)
    return round(amount, 2), shares
