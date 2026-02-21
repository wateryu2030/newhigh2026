# -*- coding: utf-8 -*-
"""
策略评分系统：最近收益、最大回撤、夏普、胜率 -> 0~1 分数，用于动态权重。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np


class StrategyScorer:
    """策略评分，输出 0–1。"""

    def __init__(
        self,
        return_weight: float = 0.3,
        drawdown_weight: float = 0.3,
        sharpe_weight: float = 0.25,
        winrate_weight: float = 0.15,
    ) -> None:
        self.return_weight = return_weight
        self.drawdown_weight = drawdown_weight
        self.sharpe_weight = sharpe_weight
        self.winrate_weight = winrate_weight

    def score(
        self,
        recent_return: float = 0.0,
        max_drawdown: float = 0.0,
        sharpe_ratio: float = 0.0,
        win_rate: float = 0.5,
    ) -> float:
        """
        综合评分 0~1。
        :param recent_return: 最近收益（小数）
        :param max_drawdown: 最大回撤（正数，小数）
        :param sharpe_ratio: 夏普比率
        :param win_rate: 胜率 0~1
        """
        s_ret = min(1.0, max(0.0, 0.5 + recent_return * 2))
        s_dd = 1.0 - min(1.0, max_drawdown / 0.20)
        s_sharpe = min(1.0, max(0.0, 0.5 + sharpe_ratio * 0.5))
        s_wr = win_rate
        return (
            self.return_weight * s_ret
            + self.drawdown_weight * s_dd
            + self.sharpe_weight * s_sharpe
            + self.winrate_weight * s_wr
        )

    def score_from_curve(self, curve: List[Dict[str, Any]]) -> float:
        """从净值曲线估算收益与回撤并打分。"""
        if not curve or len(curve) < 2:
            return 0.5
        vals = [p.get("value", 1.0) for p in curve]
        ret = (vals[-1] - vals[0]) / vals[0] if vals[0] else 0.0
        peak = vals[0]
        max_dd = 0.0
        for v in vals:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak
                if dd > max_dd:
                    max_dd = dd
        rets = [(vals[i] - vals[i - 1]) / vals[i - 1] if vals[i - 1] else 0 for i in range(1, len(vals))]
        sharpe = (np.mean(rets) / np.std(rets) * np.sqrt(252)) if len(rets) > 0 and np.std(rets) > 0 else 0.0
        return self.score(recent_return=ret, max_drawdown=max_dd, sharpe_ratio=sharpe, win_rate=0.5)
