"""
多目标适应度：收益、回撤、换手率加权综合，供进化选择。
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def composite_fitness(
    total_return: Optional[float] = None,
    sharpe_ratio: Optional[float] = None,
    max_drawdown: Optional[float] = None,
    turnover_pct: Optional[float] = None,
    *,
    weight_return: float = 0.4,
    weight_sharpe: float = 0.4,
    weight_drawdown: float = -0.2,
    weight_turnover: float = -0.05,
) -> float:
    """
    综合适应度标量。return/sharpe 越大越好，drawdown/turnover 越小越好。
    weight_drawdown 为负表示回撤越大惩罚越大；weight_turnover 为负表示换手越高惩罚越大。
    若某指标为 None 则该项不参与。
    """
    score = 0.0
    n = 0
    if total_return is not None:
        score += weight_return * (total_return if total_return > -1 else -1)
        n += 1
    if sharpe_ratio is not None:
        score += weight_sharpe * (sharpe_ratio if sharpe_ratio > -10 else 0)
        n += 1
    if max_drawdown is not None:
        # 回撤为负值，越大（越接近 0）越好
        score += weight_drawdown * (max_drawdown if max_drawdown < 0 else 0)
        n += 1
    if turnover_pct is not None:
        score += weight_turnover * (turnover_pct / 100.0 if turnover_pct >= 0 else 0)
        n += 1
    if n == 0:
        return 0.0
    return score


def fitness_from_backtest_result(result: Dict[str, Any], use_composite: bool = True) -> float:
    """
    从回测结果字典计算适应度。
    use_composite=True 时用 composite_fitness(return, sharpe, max_drawdown)；
    否则仅用 sharpe 或 total_return。
    """
    if use_composite:
        return composite_fitness(
            total_return=result.get("total_return"),
            sharpe_ratio=result.get("sharpe_ratio"),
            max_drawdown=result.get("max_drawdown"),
            turnover_pct=result.get("turnover_pct"),
        )
    sharpe = result.get("sharpe_ratio")
    if sharpe is not None:
        return float(sharpe)
    tr = result.get("total_return")
    return float(tr) if tr is not None else 0.0
