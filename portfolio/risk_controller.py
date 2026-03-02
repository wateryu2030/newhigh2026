# -*- coding: utf-8 -*-
"""
机构级风险控制器：单票≤20%、总仓≤60%，情绪周期联动仓位。
与 OpenClaw 每日报告 risk_level 一致。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 仓位上限：机构级
MAX_SINGLE_PCT = 0.20
MAX_TOTAL_PCT = 0.60

# 情绪周期 -> 总仓位上限系数（相对 MAX_TOTAL_PCT）
EMOTION_CAP = {
    "冰点": 0.25,
    "复苏": 0.45,
    "加速期": 0.60,
    "过热": 0.50,
    "退潮": 0.35,
}


def get_risk_level(
    emotion_cycle: str,
    max_drawdown: Optional[float] = None,
    index_below_ma20: bool = False,
) -> str:
    """
    综合风险等级，供 daily_report.json 与前端展示。
    :return: "低" | "中等" | "高"
    """
    if max_drawdown is not None and max_drawdown >= 0.15:
        return "高"
    if index_below_ma20 or (max_drawdown is not None and max_drawdown >= 0.10):
        return "高"
    if emotion_cycle in ("冰点", "退潮"):
        return "中等"
    if emotion_cycle in ("过热",):
        return "中等"
    return "低"


def allowed_total_position_pct(
    emotion_cycle: str,
    max_drawdown: Optional[float] = None,
) -> float:
    """
    根据情绪周期与回撤给出总仓位上限（0~1）。
    单票仍不超过 MAX_SINGLE_PCT。
    """
    cap = EMOTION_CAP.get(emotion_cycle, 0.45)
    if max_drawdown is not None:
        if max_drawdown >= 0.15:
            return 0.0
        if max_drawdown >= 0.10:
            cap = min(cap, 0.30)
    return min(MAX_TOTAL_PCT, cap)


def apply_position_limits(
    positions: Dict[str, float],
    total_equity: float,
    emotion_cycle: str = "复苏",
    max_drawdown: Optional[float] = None,
    max_positions: int = 15,
) -> Tuple[Dict[str, float], str]:
    """
    对目标仓位施加机构级约束：单票≤20%、总仓≤情绪/回撤上限。
    :param positions: { symbol: 金额 }
    :param total_equity: 总资产
    :param emotion_cycle: 情绪周期
    :param max_drawdown: 当前最大回撤
    :param max_positions: 最大持仓只数
    :return: (合规后 { symbol: 金额 }, risk_level)
    """
    if total_equity <= 0 or not positions:
        return {}, get_risk_level(emotion_cycle, max_drawdown, False)

    total_cap_pct = allowed_total_position_pct(emotion_cycle, max_drawdown)
    total_cap_amount = total_equity * total_cap_pct
    single_cap = total_equity * MAX_SINGLE_PCT

    # 按金额降序，保留前 max_positions
    sorted_syms = sorted(positions.keys(), key=lambda s: -positions.get(s, 0))
    kept = sorted_syms[:max_positions]
    out: Dict[str, float] = {}
    running = 0.0
    for s in kept:
        v = min(positions[s], single_cap)
        if v <= 0:
            continue
        if running + v > total_cap_amount:
            v = max(0.0, total_cap_amount - running)
        if v > 0:
            out[s] = round(v, 2)
            running += v
    risk_level = get_risk_level(emotion_cycle, max_drawdown, False)
    return out, risk_level
