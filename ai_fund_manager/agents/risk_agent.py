# -*- coding: utf-8 -*-
"""
风险 Agent：计算组合风险、最大仓位、止损比例。
输出：portfolio_risk, max_position, stop_loss
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RiskAgent:
    """
    风险评估 Agent。
    计算组合风险、建议最大仓位、止损比例，供资金分配与执行层使用。
    """

    def __init__(
        self,
        default_stop_loss: float = 0.08,
        max_position_cap: float = 0.95,
    ) -> None:
        self.default_stop_loss = default_stop_loss
        self.max_position_cap = max_position_cap

    def run(
        self,
        market_risk_level: float = 0.5,
        market_trend: str = "neutral",
        position_weights: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """
        执行风险评估。
        :param market_risk_level: 市场风险水平 0-1（来自 MarketAgent）。
        :param market_trend: bullish / bearish / neutral。
        :param position_weights: 当前或目标权重列表，用于估算组合波动。
        :return: {"portfolio_risk": 0-1, "max_position": 0-1, "stop_loss": 比例}
        """
        out: Dict[str, Any] = {
            "portfolio_risk": 0.3,
            "max_position": 0.7,
            "stop_loss": self.default_stop_loss,
        }
        try:
            # 组合风险：市场风险 + 分散度（权重越集中风险越高）
            portfolio_risk = market_risk_level
            if position_weights and len(position_weights) > 0:
                import numpy as np
                w = np.array(position_weights)
                w = w / (w.sum() or 1e-12)
                herfindahl = float((w ** 2).sum())
                concentration_risk = min(1.0, herfindahl * 2)
                portfolio_risk = 0.6 * market_risk_level + 0.4 * concentration_risk
            out["portfolio_risk"] = round(float(min(1.0, portfolio_risk)), 4)

            # 最大仓位：风险高则降仓位
            if market_trend == "bearish":
                base = 0.4
            elif market_trend == "bullish":
                base = 0.85
            else:
                base = 0.7
            out["max_position"] = round(
                min(self.max_position_cap, base - out["portfolio_risk"] * 0.3),
                4,
            )

            # 止损：风险高时略放宽避免频繁止损，风险低时收紧
            if out["portfolio_risk"] > 0.6:
                out["stop_loss"] = round(min(0.12, self.default_stop_loss + 0.02), 4)
            elif out["portfolio_risk"] < 0.3:
                out["stop_loss"] = round(max(0.05, self.default_stop_loss - 0.01), 4)
            else:
                out["stop_loss"] = round(self.default_stop_loss, 4)
        except Exception as e:
            logger.exception("RiskAgent run error: %s", e)
        return out
