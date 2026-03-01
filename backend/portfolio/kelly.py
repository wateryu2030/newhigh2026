# -*- coding: utf-8 -*-
"""
Kelly 公式与波动率约束仓位：私募级自动仓位。
f* = (p*b - q)/b 或 简化为 期望收益/波动率 约束，带 cap 防过度杠杆。
"""
from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np


def kelly_fraction(
    win_prob: float,
    win_loss_ratio: float,
    fraction: float = 0.25,
) -> float:
    """
    单标的 Kelly：f* = (p*b - q) / b，p=胜率，b=盈亏比，q=1-p。
    fraction: 半凯利等保守系数，默认 0.25。
    返回 [0, 1] 仓位比例。
    """
    p = max(0.0, min(1.0, win_prob))
    q = 1.0 - p
    b = max(1e-6, win_loss_ratio)
    f = (p * b - q) / b
    f = max(0.0, min(1.0, f)) * fraction
    return f


def kelly_weights_from_returns(
    returns_dict: Dict[str, List[float]],
    fraction: float = 0.25,
    target_vol: Optional[float] = 0.15,
) -> Dict[str, float]:
    """
    多标的：用历史收益估计期望与波动，得到 Kelly 权重（可再按 target_vol 缩放）。
    returns_dict: { "600519": [r1,r2,...], ... }
    target_vol: 组合目标年化波动率，None 则不缩放。
    返回: { code: weight }，和约 1。
    """
    if not returns_dict:
        return {}
    weights = {}
    for code, rets in returns_dict.items():
        arr = np.array(rets, dtype=float)
        if len(arr) < 5:
            continue
        mu = np.mean(arr)
        vol = np.std(arr)
        if vol <= 1e-8:
            vol = 1e-8
        # 简化：f ~ mu/vol^2 的 Kelly 形式，用 fraction 压降
        f = (mu / (vol ** 2)) * fraction
        f = max(0.0, min(0.5, f))
        weights[code] = f
    total = sum(weights.values())
    if total <= 0:
        return {}
    for k in weights:
        weights[k] /= total
    if target_vol is not None and target_vol > 0 and weights:
        # 组合波动近似：sqrt(w' Sigma w)，简化为加权 vol
        codes = list(weights.keys())
        vols = [np.std(returns_dict[c]) for c in codes]
        port_vol = sum(weights[c] * (vols[i] or 0) for i, c in enumerate(codes))
        if port_vol > 1e-8:
            scale = target_vol / port_vol
            scale = min(scale, 2.0)
            for k in weights:
                weights[k] *= scale
        total = sum(weights.values())
        if total > 0:
            for k in weights:
                weights[k] /= total
    return weights


def vol_target_scale(
    current_vol: float,
    target_vol: float = 0.15,
    max_scale: float = 1.5,
) -> float:
    """按目标波动率缩放总仓位。current_vol 为组合或指数近期波动率。"""
    if current_vol <= 0:
        return 1.0
    scale = target_vol / current_vol
    return max(0.1, min(max_scale, scale))
