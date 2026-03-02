# -*- coding: utf-8 -*-
"""
策略选择器：根据当前情绪/市场状态选择主策略或策略组合，供龙头池与交易计划使用。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def select_strategies(
    emotion_cycle: str,
    regime: Optional[str] = None,
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    根据情绪周期与市场状态返回策略权重。
    :param emotion_cycle: 冰点/复苏/加速期/过热/退潮
    :param regime: BULL/BEAR/NEUTRAL，可选
    :param custom_weights: AI 优化后的权重，若提供则优先使用
    :return: {"dragon_strategy": 0.4, "trend_strategy": 0.3, "mean_reversion": 0.3}
    """
    if custom_weights:
        total = sum(custom_weights.values())
        if total > 0:
            return {k: v / total for k, v in custom_weights.items()}

    # 情绪周期微调：冰点/退潮偏均值回归，加速期偏龙头
    base = {"dragon_strategy": 0.40, "trend_strategy": 0.30, "mean_reversion": 0.30}
    if emotion_cycle in ("冰点", "退潮"):
        base = {"dragon_strategy": 0.25, "trend_strategy": 0.25, "mean_reversion": 0.50}
    elif emotion_cycle in ("加速期", "过热"):
        base = {"dragon_strategy": 0.50, "trend_strategy": 0.30, "mean_reversion": 0.20}
    if regime == "BEAR":
        base["mean_reversion"] = min(0.5, base["mean_reversion"] + 0.15)
        base["dragon_strategy"] = max(0.2, base["dragon_strategy"] - 0.1)
        total = sum(base.values())
        base = {k: v / total for k, v in base.items()}
    return base
