# -*- coding: utf-8 -*-
"""
多策略组合骨架：策略权重、portfolio_allocator、组合调度。
资金按标的权重分配；组合调度按策略权重融合信号并驱动分配结果。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

# 策略权重：strategy_id -> weight（归一化后 0~1）
StrategyWeights = Dict[str, float]


def allocate(
    capital: float,
    symbol_weights: Dict[str, float],
    method: str = "equal",
) -> Dict[str, float]:
    """
    将总资金按标的权重分配到各 symbol。
    :param capital: 总资金
    :param symbol_weights: 标的权重（可未归一化），如 {"000001.XSHE": 0.5, "600000.XSHG": 0.5}
    :param method: 目前仅 "equal"（按权重比例）；risk_parity / vol_target 等见 portfolio.allocator
    :return: { symbol: 分配金额 }
    """
    if capital <= 0 or not symbol_weights:
        return {}
    w = list(symbol_weights.values())
    s = sum(w)
    if s <= 0:
        symbols = list(symbol_weights.keys())
        s = len(symbols)
        w = [1.0 / s] * s
    else:
        w = [x / s for x in w]
        symbols = list(symbol_weights.keys())
    return {sym: capital * w[i] for i, sym in enumerate(symbols)}


def normalize_weights(weights: Optional[List[float]], n: int) -> List[float]:
    """策略权重归一化；None 或长度不匹配则等权。"""
    if not n:
        return []
    if weights is None or len(weights) != n:
        return [1.0 / n] * n
    s = sum(weights)
    if s <= 0:
        return [1.0 / n] * n
    return [x / s for x in weights]


class CombinedScheduler:
    """
    组合调度：多策略按权重融合信号，产出组合信号序列（与可选目标分配）。
    不依赖回测引擎，仅做信号融合；回测/执行由上层用 PortfolioEngine 或 ExecutionEngine 完成。
    """

    def __init__(
        self,
        strategy_ids: List[str],
        weights: Optional[List[float]] = None,
    ):
        self.strategy_ids = strategy_ids
        self.weights = normalize_weights(weights, len(strategy_ids))

    def combine_signals(self, signals_per_strategy: List[List[str]]) -> List[str]:
        """
        按日融合多策略信号。每日各策略一个信号（BUY/SELL/HOLD），按权重加权投票。
        :param signals_per_strategy: [ strategy0_signals_by_date, strategy1_signals_by_date, ... ]，长度与 strategy_ids 一致
        :return: 按日对齐的组合信号列表（与最短一条长度一致）
        """
        if not signals_per_strategy or not self.weights:
            return []
        n_dates = min(len(s) for s in signals_per_strategy)
        if n_dates == 0:
            return []
        out = []
        for i in range(n_dates):
            w_sum = 0.0
            for j, sigs in enumerate(signals_per_strategy):
                s = (sigs[i] or "HOLD").upper()
                w = self.weights[j] if j < len(self.weights) else 0
                if s == "BUY":
                    w_sum += w
                elif s == "SELL":
                    w_sum -= w
            if w_sum > 0.3:
                out.append("BUY")
            elif w_sum < -0.3:
                out.append("SELL")
            else:
                out.append("HOLD")
        return out

    def combine_signal_single_day(self, signals: List[str]) -> str:
        """单日多策略信号融合。"""
        if not signals:
            return "HOLD"
        w_sum = 0.0
        for j, s in enumerate(signals):
            s = (s or "HOLD").upper()
            w = self.weights[j] if j < len(self.weights) else 0
            if s == "BUY":
                w_sum += w
            elif s == "SELL":
                w_sum -= w
        if w_sum > 0.3:
            return "BUY"
        if w_sum < -0.3:
            return "SELL"
        return "HOLD"
