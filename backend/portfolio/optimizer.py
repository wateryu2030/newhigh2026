# -*- coding: utf-8 -*-
"""
组合优化引擎：按因子得分、风险平价、波动率控制分配权重。
生产级：支持 risk_parity、Kelly 扩展。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np


class PortfolioOptimizer:
    """按候选标的 score 归一化得到权重；可扩展风险平价等。"""

    def __init__(self, score_key: str = "score", min_score: float = 0.0):
        self.score_key = score_key
        self.min_score = min_score

    def optimize(self, candidates: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        candidates: [{"code": "600519", "score": 0.8}, ...]
        返回: {"600519": 0.25, "000001": 0.75, ...} 权重和为 1。
        """
        if not candidates:
            return {}
        code_key = "code" if "code" in candidates[0] else "symbol"
        total = sum(max(float(c.get(self.score_key, 0) or 0), self.min_score) for c in candidates)
        if total <= 0:
            n = len(candidates)
            return {str(c.get(code_key, "")): 1.0 / n for c in candidates if c.get(code_key)}
        weights = {}
        for c in candidates:
            code = str(c.get(code_key, ""))
            if not code:
                continue
            s = max(float(c.get(self.score_key, 0) or 0), self.min_score)
            weights[code] = s / total
        return weights

    def risk_parity(self, returns: np.ndarray) -> np.ndarray:
        """
        风险平价：按波动率倒数分配权重。
        returns: (n_assets, n_periods) 或 (n_periods,) 单资产。
        返回权重向量，和为 1。
        """
        if returns is None or returns.size == 0:
            return np.array([])
        r = np.atleast_2d(returns)
        if r.shape[0] == 1:
            return np.array([1.0])
        vol = np.std(r, axis=1)
        vol = np.where(vol <= 0, 1e-8, vol)
        inv_vol = 1.0 / vol
        w = inv_vol / np.sum(inv_vol)
        return w

    def risk_parity_weights(self, returns_dict: Dict[str, List[float]]) -> Dict[str, float]:
        """returns_dict: { "600519": [r1,r2,...], "000001": [...] }，返回 { code: weight }。"""
        if not returns_dict:
            return {}
        codes = list(returns_dict.keys())
        arr = np.array([returns_dict[c] for c in codes], dtype=float)
        n = arr.shape[0]
        if n == 0:
            return {}
        # 对齐长度
        min_len = min(len(returns_dict[c]) for c in codes)
        arr = np.array([returns_dict[c][-min_len:] for c in codes])
        vol = np.std(arr, axis=1)
        vol = np.where(vol <= 0, 1e-8, vol)
        inv_vol = 1.0 / vol
        w = inv_vol / np.sum(inv_vol)
        return {codes[i]: float(w[i]) for i in range(n)}

    def kelly_weights(
        self,
        returns_dict: Dict[str, List[float]],
        fraction: float = 0.25,
        target_vol: Optional[float] = 0.15,
    ) -> Dict[str, float]:
        """Kelly 权重 + 波动率约束，委托 kelly 模块。"""
        from .kelly import kelly_weights_from_returns
        return kelly_weights_from_returns(returns_dict, fraction=fraction, target_vol=target_vol)
