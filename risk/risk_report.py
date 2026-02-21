# -*- coding: utf-8 -*-
"""
风险报告：每日风险状态、回撤、仓位、风险等级。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from .risk_engine import RiskEngine, RiskLevel


@dataclass
class RiskReport:
    """单日风险报告。"""
    date: str
    max_drawdown: float
    position_ratio: float
    risk_level: RiskLevel
    message: str = ""


class RiskReporter:
    """
    生成每日风险报告。
    - 当前回撤
    - 仓位比例
    - 风险等级
    """

    def __init__(self, risk_engine: Optional[RiskEngine] = None):
        self.risk_engine = risk_engine or RiskEngine()

    def report(
        self,
        date: str,
        max_drawdown: float,
        position_value: float,
        total_equity: float,
        index_df: Optional[pd.DataFrame] = None,
    ) -> RiskReport:
        """
        生成当日风险报告。
        """
        risk_level = self.risk_engine.get_risk_status(max_drawdown, index_df)
        pos_ratio = position_value / total_equity if total_equity > 0 else 0.0
        msg = self._format_message(risk_level, max_drawdown, pos_ratio)
        return RiskReport(
            date=date,
            max_drawdown=max_drawdown,
            position_ratio=pos_ratio,
            risk_level=risk_level,
            message=msg,
        )

    def _format_message(
        self,
        risk_level: RiskLevel,
        max_drawdown: float,
        position_ratio: float,
    ) -> str:
        msg = f"风险等级: {risk_level.value} | 最大回撤: {max_drawdown:.2%} | 仓位: {position_ratio:.1%}"
        if risk_level == RiskLevel.STOP:
            msg += " [建议停止交易]"
        elif risk_level == RiskLevel.HIGH:
            msg += " [建议降低仓位]"
        return msg
