# -*- coding: utf-8 -*-
"""
仓位管理：基于风险预算模型，根据信号与账户状态计算建议仓位（金额或比例）。
"""
from __future__ import annotations
from typing import Any, Dict


def calculate_position(signal: Dict[str, Any], account: Dict[str, Any]) -> float:
    """
    风险预算模型：根据信号置信度与账户风险额度计算建议仓位比例（0~1）。
    signal: {"symbol": "000001", "action": "BUY", "confidence": 0.82, ...}
    account: {"total_asset": float, "cash": float, "positions": {...}, "risk_budget": float 可选}
    返回: 建议仓位占净资产比例，BUY 时有效；SELL 时由持仓决定，此处返回 0 表示全平或按持仓量。
    """
    if not signal or not account:
        return 0.0
    action = (signal.get("action") or "").upper()
    if action == "SELL":
        return 0.0
    if action != "BUY":
        return 0.0

    total = float(account.get("total_asset") or 0)
    if total <= 0:
        return 0.0
    confidence = float(signal.get("confidence") or 0.5)
    confidence = max(0.0, min(1.0, confidence))

    risk_budget = float(account.get("risk_budget") or 0.2)
    risk_budget = max(0.05, min(0.25, risk_budget))
    base_weight = risk_budget * confidence
    positions = account.get("positions") or {}
    symbol = (signal.get("symbol") or "").strip()
    current_weight = float(
        (positions.get(symbol) or positions.get(symbol + ".XSHE") or positions.get(symbol + ".XSHG") or {}).get("weight") or 0
    )
    add_weight = max(0.0, min(0.2 - current_weight, base_weight))
    return round(add_weight, 4)
