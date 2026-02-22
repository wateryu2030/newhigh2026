# -*- coding: utf-8 -*-
"""
强化学习分配器（占位）：后续可接入 PPO 等，由 AI 学习何时重仓/轻仓。
"""
from __future__ import annotations
from typing import Any, Dict, List
import numpy as np


class ReinforcementAllocator:
    def allocate(self, metrics: List[Dict[str, Any]], state: Dict[str, Any] = None) -> np.ndarray:
        """占位：当前与 AIAllocator 一致，按夏普分配。"""
        if not metrics:
            return np.array([])
        sharpe = np.array([m.get("sharpe", 0) for m in metrics], dtype=float)
        sharpe = np.maximum(sharpe, 0)
        s = sharpe.sum()
        if s < 1e-12:
            return np.ones(len(metrics)) / len(metrics)
        return sharpe / s
