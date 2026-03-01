# -*- coding: utf-8 -*-
"""
AI 选股因子模型：多因子加权评分，供组合优化使用。
可与 backend.ai.alpha_model 的 LightGBM 预测结合使用。
"""
from __future__ import annotations
from typing import Any, Dict


class AlphaFactorModel:
    """因子评分：rps、momentum、fund_flow、volatility 加权。"""

    def __init__(
        self,
        w_rps: float = 0.3,
        w_momentum: float = 0.2,
        w_fund_flow: float = 0.3,
        w_volatility: float = 0.2,
    ):
        self.w_rps = w_rps
        self.w_momentum = w_momentum
        self.w_fund_flow = w_fund_flow
        self.w_volatility = w_volatility

    def score(self, stock: Dict[str, Any]) -> float:
        """单只股票综合得分，缺省因子按 0 处理。"""
        rps = float(stock.get("rps", 0) or 0)
        momentum = float(stock.get("momentum", 0) or 0)
        fund_flow = float(stock.get("fund_flow", 0) or 0)
        volatility = float(stock.get("volatility", 0) or 0)
        return (
            rps * self.w_rps
            + momentum * self.w_momentum
            + fund_flow * self.w_fund_flow
            + volatility * self.w_volatility
        )

    def score_batch(self, stocks: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """批量评分，每项增加 score 字段。"""
        out = []
        for s in stocks:
            s = dict(s)
            s["score"] = self.score(s)
            out.append(s)
        return out
