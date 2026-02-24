# -*- coding: utf-8 -*-
"""
策略评估器：根据回测结果计算评分。
公式: score = 0.4 * return + 0.3 * sharpe - 0.3 * drawdown
"""
from __future__ import annotations
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 权重可配置
WEIGHT_RETURN = 0.4
WEIGHT_SHARPE = 0.3
WEIGHT_DRAWDOWN = 0.3


class StrategyEvaluator:
    """根据 return / sharpe / drawdown 计算单一评分。"""

    def __init__(
        self,
        weight_return: float = WEIGHT_RETURN,
        weight_sharpe: float = WEIGHT_SHARPE,
        weight_drawdown: float = WEIGHT_DRAWDOWN,
    ) -> None:
        self.weight_return = weight_return
        self.weight_sharpe = weight_sharpe
        self.weight_drawdown = weight_drawdown

    def evaluate(self, metrics: Dict[str, float]) -> float:
        """
        根据回测指标计算评分。
        :param metrics: 至少包含 "return", "sharpe", "drawdown"
        :return: 综合得分，越高越好
        """
        r = float(metrics.get("return", 0.0))
        s = float(metrics.get("sharpe", 0.0))
        d = float(metrics.get("drawdown", 0.0))
        score = (
            self.weight_return * r
            + self.weight_sharpe * s
            - self.weight_drawdown * d
        )
        logger.debug("Evaluate: return=%.4f sharpe=%.4f drawdown=%.4f -> score=%.4f", r, s, d, score)
        return round(score, 6)

    def evaluate_from_backtest_result(self, backtest_result: Dict[str, Any]) -> float:
        """从 backtest_engine 返回的 dict 中取 return/sharpe/drawdown 并评分。"""
        return self.evaluate(backtest_result)
