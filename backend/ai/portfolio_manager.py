# -*- coding: utf-8 -*-
"""
组合管理：根据预测收益生成权重，归一化、单股上限 20%、最多 10 只。
"""
from __future__ import annotations
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

MAX_WEIGHT_PER_STOCK = 0.20
MAX_HOLDINGS = 10


def optimize_weights(
    predicted_returns: pd.Series,
    current_weights: Optional[Dict[str, float]] = None,
    max_weight: float = MAX_WEIGHT_PER_STOCK,
    max_stocks: int = MAX_HOLDINGS,
) -> pd.Series:
    """
    根据预测收益生成组合权重。
    predicted_returns: index=symbol, value=预测收益（如未来5日收益）。
    返回: index=symbol, value=权重 (0~1)，已归一化。
    """
    if predicted_returns is None or len(predicted_returns) == 0:
        return pd.Series(dtype=float)
    current_weights = current_weights or {}
    pred = predicted_returns.dropna().sort_values(ascending=False)
    pred = pred[pred > 0]
    if len(pred) == 0:
        return pd.Series(dtype=float)
    top = pred.head(max_stocks)
    raw = top / (top.sum() + 1e-10)
    raw = raw.clip(upper=max_weight)
    w = raw / raw.sum()
    return w


def weights_to_target_positions(
    weights: pd.Series,
    total_asset: float,
    prices: Dict[str, float],
) -> Dict[str, int]:
    """将权重转为各标的目标股数（整百）。"""
    if total_asset <= 0 or weights is None or len(weights) == 0:
        return {}
    out = {}
    for sym, w in weights.items():
        p = prices.get(sym)
        if p is None or p <= 0:
            continue
        value = total_asset * w
        qty = int(value / p) // 100 * 100
        if qty >= 100:
            out[sym] = qty
    return out
