#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略工具函数
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional


def normalize_score(scores: Dict[str, float]) -> Dict[str, float]:
    """归一化得分到0-100"""
    if not scores:
        return {}
    min_score = min(scores.values())
    max_score = max(scores.values())
    if max_score == min_score:
        return {k: 50 for k in scores.keys()}
    return {k: (v - min_score) / (max_score - min_score) * 100 for k, v in scores.items()}


def calculate_ma(prices: np.ndarray, window: int) -> float:
    """计算移动平均"""
    if len(prices) < window:
        return np.nan
    return np.mean(prices[-window:])


def calculate_momentum(prices: np.ndarray, window: int) -> float:
    """计算动量（收益率）"""
    if len(prices) < window:
        return np.nan
    return (prices[-1] - prices[0]) / prices[0]


def check_mean_reversion(current_price: float, ma20: float, threshold: float = 0.1) -> bool:
    """检查是否满足均值回归条件"""
    return current_price < ma20 * (1 - threshold)


def check_volume_shrinkage(current_vol: float, ma20_vol: float, ratio: float = 0.8) -> bool:
    """检查是否缩量"""
    return current_vol < ma20_vol * ratio


def get_top_percent(items: List[tuple], percent: float = 0.1) -> List[tuple]:
    """获取前percent百分比的项"""
    if not items:
        return []
    count = max(1, int(len(items) * percent))
    return sorted(items, key=lambda x: x[1], reverse=True)[:count]
