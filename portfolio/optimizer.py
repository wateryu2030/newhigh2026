# -*- coding: utf-8 -*-
"""
组合优化器：Mean Variance、最大夏普、最小方差，使用 scipy.optimize。
"""
from __future__ import annotations
from typing import Dict, List, Optional
import numpy as np


def mean_variance(
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    target_return: Optional[float] = None,
) -> np.ndarray:
    """
    均值-方差优化。若 target_return 给定则在该收益下最小化方差；否则最大化 (收益 - 风险惩罚)。
    :return: 权重向量，和为 1
    """
    n = len(expected_returns)
    if n == 0 or cov_matrix.shape[0] != n:
        return np.array([])
    try:
        from scipy.optimize import minimize
    except ImportError:
        return np.ones(n) / n
    cov = np.asarray(cov_matrix, dtype=float)
    if cov.size == 1:
        cov = np.eye(n) * max(float(cov.flat[0]), 1e-8)
    cov = np.where(np.isfinite(cov), cov, 0)
    er = np.asarray(expected_returns, dtype=float).ravel()[:n]

    def variance(w):
        return w @ cov @ w

    def neg_sharpe(w):
        if w @ cov @ w <= 0:
            return 1e10
        return -(w @ er) / np.sqrt(w @ cov @ w)

    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    bounds = [(0.0, 1.0)] * n
    x0 = np.ones(n) / n
    if target_return is not None:
        constraints.append({"type": "eq", "fun": lambda w: w @ er - target_return})
        res = minimize(variance, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    else:
        res = minimize(neg_sharpe, x0, method="SLSQP", bounds=bounds, constraints=constraints)
    if res.success and res.x is not None:
        w = np.maximum(res.x, 0)
        w = w / w.sum()
        return w
    return np.ones(n) / n


def max_sharpe(expected_returns: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
    """最大夏普权重。"""
    return mean_variance(expected_returns, cov_matrix, target_return=None)


def min_variance(expected_returns: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
    """最小方差组合（不约束收益）。"""
    n = len(expected_returns)
    if n == 0:
        return np.array([])
    try:
        from scipy.optimize import minimize
    except ImportError:
        return np.ones(n) / n
    cov = np.asarray(cov_matrix, dtype=float)
    if cov.shape[0] != n:
        cov = np.eye(n) * 0.1
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]
    bounds = [(0.0, 1.0)] * n
    res = minimize(lambda w: w @ cov @ w, np.ones(n) / n, method="SLSQP", bounds=bounds, constraints=constraints)
    if res.success and res.x is not None:
        w = np.maximum(res.x, 0)
        return w / w.sum()
    return np.ones(n) / n
