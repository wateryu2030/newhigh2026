# -*- coding: utf-8 -*-
"""
资金分配引擎：等权重、风险平价、Kelly、最大夏普。
输入：股票评分 + 风险参数；输出：最终仓位 {code: weight}。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _to_score_list(stock_scores: List[Dict[str, Any]]) -> List[tuple]:
    """[(code, score), ...] 按 score 降序。"""
    return [(x["code"], x["score"]) for x in sorted(stock_scores, key=lambda s: s["score"], reverse=True)]


def equal_weight(
    stock_scores: List[Dict[str, Any]],
    top_n: int = 10,
    max_position: float = 1.0,
) -> Dict[str, float]:
    """等权重：取 top_n 只，每只 1/top_n，总和不超 max_position。"""
    pairs = _to_score_list(stock_scores)[:top_n]
    if not pairs:
        return {}
    n = len(pairs)
    w = max_position / n
    return {code: round(w, 6) for code, _ in pairs}


def risk_parity(
    stock_scores: List[Dict[str, Any]],
    top_n: int = 10,
    max_position: float = 1.0,
    volatilities: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    风险平价：权重与波动率成反比，使各资产风险贡献相近。
    volatilities 缺失时用 1/score 近似（低分视为高风险）。
    """
    pairs = _to_score_list(stock_scores)[:top_n]
    if not pairs:
        return {}
    inv_vol = []
    for code, score in pairs:
        if volatilities and code in volatilities and volatilities[code] > 0:
            inv_vol.append((code, 1.0 / volatilities[code]))
        else:
            inv_vol.append((code, max(0.1, score)))
    total = sum(v for _, v in inv_vol)
    if total <= 0:
        return equal_weight(stock_scores, top_n, max_position)
    return {code: round(max_position * v / total, 6) for code, v in inv_vol}


def kelly(
    stock_scores: List[Dict[str, Any]],
    top_n: int = 10,
    max_position: float = 1.0,
    kelly_fraction: float = 0.25,
) -> Dict[str, float]:
    """
    Kelly 公式：f = (p*b - q)/b 简化为用 score 近似胜率与赔率。
    这里用 score 作为期望收益的代理，单只上限 kelly_fraction。
    """
    pairs = _to_score_list(stock_scores)[:top_n]
    if not pairs:
        return {}
    total_score = sum(s for _, s in pairs)
    if total_score <= 0:
        return equal_weight(stock_scores, top_n, max_position)
    weights = {}
    for code, score in pairs:
        f = min(kelly_fraction, max(0.01, score / 2))
        weights[code] = f
    s = sum(weights.values())
    if s > 0:
        weights = {c: round(max_position * w / s, 6) for c, w in weights.items()}
    return weights


def max_sharpe(
    stock_scores: List[Dict[str, Any]],
    top_n: int = 10,
    max_position: float = 1.0,
    returns: Optional[Dict[str, float]] = None,
    volatilities: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """
    最大夏普：在无风险利率为 0 的简化下，权重与 (收益/波动) 成正比。
    returns/volatilities 缺失时用 score 作为收益代理、常数波动。
    """
    pairs = _to_score_list(stock_scores)[:top_n]
    if not pairs:
        return {}
    sharpe_contrib = []
    for code, score in pairs:
        ret = (returns.get(code, score)) if returns else score
        vol = (volatilities.get(code, 0.2)) if volatilities else 0.2
        if vol <= 0:
            vol = 0.2
        sharpe_contrib.append((code, ret / vol))
    total = sum(v for _, v in sharpe_contrib)
    if total <= 0:
        return equal_weight(stock_scores, top_n, max_position)
    return {code: round(max_position * v / total, 6) for code, v in sharpe_contrib}


class PortfolioOptimizer:
    """
    资金分配引擎。支持等权重、风险平价、Kelly、最大夏普四种方式。
    """

    def __init__(
        self,
        method: str = "equal_weight",
        top_n: int = 10,
        max_position: float = 1.0,
    ) -> None:
        self.method = method
        self.top_n = top_n
        self.max_position = max_position

    def run(
        self,
        stock_scores: List[Dict[str, Any]],
        risk_params: Optional[Dict[str, Any]] = None,
        max_position_override: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        根据股票评分与风险参数生成最终仓位。
        :param stock_scores: [{"code": "600519", "score": 0.82}, ...]
        :param risk_params: 来自 RiskAgent，含 max_position 等，会覆盖默认。
        :param max_position_override: 若提供，优先用于总仓位上限。
        :return: {"600519": 0.2, "000001": 0.15, ...}
        """
        risk_params = risk_params or {}
        max_pos = max_position_override or risk_params.get("max_position") or self.max_position
        max_pos = min(1.0, max(0.01, max_pos))
        try:
            if self.method == "risk_parity":
                return risk_parity(stock_scores, self.top_n, max_pos, risk_params.get("volatilities"))
            if self.method == "kelly":
                return kelly(stock_scores, self.top_n, max_pos, risk_params.get("kelly_fraction", 0.25))
            if self.method == "max_sharpe":
                return max_sharpe(
                    stock_scores,
                    self.top_n,
                    max_pos,
                    risk_params.get("returns"),
                    risk_params.get("volatilities"),
                )
            return equal_weight(stock_scores, self.top_n, max_pos)
        except Exception as e:
            logger.exception("PortfolioOptimizer run error: %s", e)
            return equal_weight(stock_scores, self.top_n, max_pos)
