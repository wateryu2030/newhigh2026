# -*- coding: utf-8 -*-
"""
订单状态机：NEW → SUBMITTED → PARTIAL_FILLED / FILLED / CANCELLED / REJECTED
"""
from __future__ import annotations
from enum import Enum
from typing import Set

# 订单状态
OrderStatus = Enum(
    "OrderStatus",
    [
        "NEW",           # 已创建未提交
        "SUBMITTED",     # 已提交待成交
        "PARTIAL_FILLED", # 部分成交
        "FILLED",        # 全部成交
        "CANCELLED",     # 已撤单
        "REJECTED",      # 已拒绝
    ],
)
NEW = OrderStatus.NEW
SUBMITTED = OrderStatus.SUBMITTED
PARTIAL_FILLED = OrderStatus.PARTIAL_FILLED
FILLED = OrderStatus.FILLED
CANCELLED = OrderStatus.CANCELLED
REJECTED = OrderStatus.REJECTED

# 允许的状态转换
_TRANSITIONS: dict[OrderStatus, Set[OrderStatus]] = {
    NEW: {SUBMITTED, REJECTED},
    SUBMITTED: {PARTIAL_FILLED, FILLED, CANCELLED, REJECTED},
    PARTIAL_FILLED: {FILLED, CANCELLED},
    FILLED: set(),
    CANCELLED: set(),
    REJECTED: set(),
}


def can_transition(from_status: OrderStatus, to_status: OrderStatus) -> bool:
    """是否允许从 from_status 转换到 to_status。"""
    return to_status in _TRANSITIONS.get(from_status, set())


def is_terminal(status: OrderStatus) -> bool:
    """是否终态（不可再变更）。"""
    return status in (FILLED, CANCELLED, REJECTED)


def status_to_str(status: OrderStatus) -> str:
    """状态枚举转小写字符串，便于序列化。"""
    return status.name.lower() if status else ""


def str_to_status(s: str) -> OrderStatus:
    """字符串转状态枚举。"""
    if not s:
        return NEW
    u = (s or "").strip().upper()
    for st in OrderStatus:
        if st.name == u:
            return st
    return NEW
