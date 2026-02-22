# -*- coding: utf-8 -*-
"""
AI 资金分配器：根据策略指标（如夏普）分配权重，可扩展为 RL。
"""
from __future__ import annotations
from typing import Any, Dict, List, Union
import numpy as np


class AIAllocator:
    def allocate(self, metrics: List[Dict[str, Any]]) -> np.ndarray:
        """按夏普（非负）归一化得到权重。"""
        if not metrics:
            return np.array([])
        sharpe = np.array([m.get("sharpe", 0) for m in metrics], dtype=float)
        sharpe = np.maximum(sharpe, 0)
        s = sharpe.sum()
        if s < 1e-12:
            return np.ones(len(metrics)) / len(metrics)
        return sharpe / s
