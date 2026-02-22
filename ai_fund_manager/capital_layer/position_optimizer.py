# -*- coding: utf-8 -*-
"""
资金分配优化器：等权、风险平价、最大夏普等。
"""
from __future__ import annotations
from typing import Union
import numpy as np


class PositionOptimizer:
    def equal_weight(self, n: int) -> np.ndarray:
        return np.ones(n) / max(n, 1)

    def risk_parity(self, vols: Union[list, np.ndarray]) -> np.ndarray:
        vols = np.asarray(vols, dtype=float)
        inv = 1.0 / (vols + 1e-6)
        w = inv / inv.sum()
        return w

    def max_sharpe_approx(self, returns_matrix: np.ndarray) -> np.ndarray:
        """近似最大夏普：用历史收益均值归一化（简化版）。"""
        if returns_matrix.size == 0 or returns_matrix.shape[0] == 0:
            return np.array([])
        mu = np.mean(returns_matrix, axis=0)
        mu = np.maximum(mu, 0)
        if mu.sum() < 1e-12:
            return np.ones(len(mu)) / len(mu)
        return mu / mu.sum()
