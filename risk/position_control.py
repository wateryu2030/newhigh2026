# -*- coding: utf-8 -*-
"""
仓位控制：单股最大 20%、总仓位 80%，根据风险状态自动调整。
"""
from __future__ import annotations
from typing import Dict, Optional
from .risk_engine import RiskEngine, RiskLevel


class PositionControl:
    """
    仓位控制。
    - 单股最大仓位 20%
    - 总仓位上限 80%
    - 根据风险状态自动调整仓位比例
    """

    def __init__(
        self,
        max_single_position: float = 0.20,
        max_total_position: float = 0.80,
    ):
        self.max_single_position = max_single_position
        self.max_total_position = max_total_position
        self._risk_engine = RiskEngine()

    def get_position_ratio(self, risk_level: RiskLevel) -> float:
        """
        根据风险等级返回可用仓位比例。
        - LOW: 100%
        - NORMAL: 80%
        - HIGH: 50%
        - STOP: 0%
        """
        ratio_map = {
            RiskLevel.LOW: 1.0,
            RiskLevel.NORMAL: 0.80,
            RiskLevel.HIGH: 0.50,
            RiskLevel.STOP: 0.0,
        }
        return ratio_map.get(risk_level, 0.5)

    def max_buy_value(
        self,
        total_equity: float,
        current_position_value: float,
        single_symbol_value: float,
        risk_level: RiskLevel,
    ) -> float:
        """
        计算单股最大可买入金额。
        :param total_equity: 总资产
        :param current_position_value: 当前持仓总市值
        :param single_symbol_value: 该标的当前持仓市值
        :param risk_level: 风险等级
        """
        base_ratio = self.get_position_ratio(risk_level)
        max_total = total_equity * self.max_total_position * base_ratio
        max_single = total_equity * self.max_single_position * base_ratio
        remaining_total = max(0, max_total - current_position_value)
        remaining_single = max(0, max_single - single_symbol_value)
        return min(remaining_total, remaining_single)
