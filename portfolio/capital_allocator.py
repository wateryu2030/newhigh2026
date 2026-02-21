# -*- coding: utf-8 -*-
"""
资金分配器：机构核心算法 — 等权 / 风险平价 / 夏普最大化。
"""
from typing import Any, Dict, List, Optional, Union
import numpy as np


class CapitalAllocator:
    """
    根据策略列表与总资金，分配各策略资金。
    支持：等权 / 自定义权重 / 风险平价 / 夏普最大化。
    """

    def allocate(
        self,
        capital: float,
        strategies: List[Any],
        weights: Optional[List[float]] = None,
    ) -> Dict[Any, float]:
        """
        :param capital: 总资金
        :param strategies: 策略列表（或策略 id 列表）
        :param weights: 各策略权重；None 表示等权
        :return: { strategy: allocated_capital }
        """
        n = len(strategies)
        if n == 0:
            return {}
        w = self._normalize(weights, n)
        total = sum(w)
        if total <= 0:
            w = [1.0 / n] * n
        return {s: capital * (w[i] / sum(w)) for i, s in enumerate(strategies)}

    def _normalize(self, weights: Optional[List[float]], n: int) -> List[float]:
        if weights is None or len(weights) != n:
            return [1.0 / n] * n
        s = sum(weights)
        return [w / s for w in weights] if s > 0 else [1.0 / n] * n

    def allocate_risk_parity(
        self,
        capital: float,
        strategies: List[Any],
        volatilities: List[float],
    ) -> Dict[Any, float]:
        """
        风险平价：按波动率倒数分配，波动率低者权重高。
        :param volatilities: 各策略年化波动率
        """
        n = len(strategies)
        if n == 0:
            return {}
        vols = np.asarray(volatilities, dtype=float)
        vols = np.where(vols <= 0, np.nan, vols)
        inv_vol = 1.0 / np.where(np.isnan(vols), 1e6, vols)
        inv_vol = np.where(np.isnan(inv_vol), 0, inv_vol)
        if inv_vol.sum() <= 0:
            return {s: capital / n for s in strategies}
        w = inv_vol / inv_vol.sum()
        return {s: capital * w[i] for i, s in enumerate(strategies)}

    def allocate_max_sharpe(
        self,
        capital: float,
        strategies: List[Any],
        returns: List[float],
        volatilities: List[float],
        correlation: Optional[np.ndarray] = None,
    ) -> Dict[Any, float]:
        """
        夏普最大化：在给定收益、波动率（及可选相关性）下求最优权重。
        简化版：按夏普比 = return/vol 比例分配。
        """
        n = len(strategies)
        if n == 0:
            return {}
        rets = np.asarray(returns, dtype=float)
        vols = np.asarray(volatilities, dtype=float)
        vols = np.where(vols <= 0, 1e-6, vols)
        sharpe = rets / vols
        sharpe = np.where(np.isnan(sharpe) | (sharpe < 0), 0, sharpe)
        if sharpe.sum() <= 0:
            return {s: capital / n for s in strategies}
        w = sharpe / sharpe.sum()
        return {s: capital * w[i] for i, s in enumerate(strategies)}
