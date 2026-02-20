# -*- coding: utf-8 -*-
"""
资金曲线自适应仓位控制：根据风险概率动态调整可投入资金，活着比赚钱重要。
"""
from typing import Optional


class PositionSizer:
    """
    根据 risk_prob（如 RiskModel 输出的回撤/爆仓概率）决定可用资金比例。
    风险高时降仓，风险低时可满仓（或按策略上限）。
    """

    def __init__(
        self,
        high_risk_threshold: float = 0.7,
        mid_risk_threshold: float = 0.4,
        high_risk_ratio: float = 0.2,
        mid_risk_ratio: float = 0.5,
        low_risk_ratio: float = 1.0,
    ):
        self.high_risk_threshold = high_risk_threshold
        self.mid_risk_threshold = mid_risk_threshold
        self.high_risk_ratio = high_risk_ratio
        self.mid_risk_ratio = mid_risk_ratio
        self.low_risk_ratio = low_risk_ratio

    def size(self, capital: float, risk_prob: float) -> float:
        """
        :param capital: 总资金
        :param risk_prob: 风险概率 ∈ [0, 1]
        :return: 本笔可用的资金/仓位上限
        """
        if risk_prob >= self.high_risk_threshold:
            return capital * self.high_risk_ratio
        if risk_prob >= self.mid_risk_threshold:
            return capital * self.mid_risk_ratio
        return capital * self.low_risk_ratio
