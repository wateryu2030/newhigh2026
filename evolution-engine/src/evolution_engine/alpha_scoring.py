"""
Alpha Scoring Engine — Alpha 评分系统
基于回测指标 + 风险指标计算综合 Alpha 分，用于策略入池与排序
"""

from typing import Any, Dict, Optional


def alpha_score(
    sharpe_ratio: Optional[float] = None,
    sortino_ratio: Optional[float] = None,
    max_drawdown: Optional[float] = None,
    win_rate_pct: Optional[float] = None,
    profit_factor: Optional[float] = None,
    total_return: Optional[float] = None,
    *,
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    综合 Alpha 分 [0, 1]（越高越好）。
    默认：Sharpe/Sortino 正向，Drawdown 负向，WinRate/ProfitFactor 正向。
    """
    w = weights or {
        "sharpe": 0.25,
        "sortino": 0.20,
        "drawdown": 0.25,
        "win_rate": 0.15,
        "profit_factor": 0.15,
    }
    score = 0.0
    if sharpe_ratio is not None:
        # 归一化到 0~1，假设 2.0 为优秀
        score += w["sharpe"] * min(1.0, max(0.0, sharpe_ratio / 2.0))
    if sortino_ratio is not None:
        score += w["sortino"] * min(1.0, max(0.0, sortino_ratio / 2.0))
    if max_drawdown is not None:
        # 回撤越小越好，10% 回撤 = 0.5 分
        score += w["drawdown"] * max(0.0, 1.0 - (max_drawdown or 0) / 0.2)
    if win_rate_pct is not None:
        score += w["win_rate"] * (win_rate_pct / 100.0)
    if profit_factor is not None:
        score += w["profit_factor"] * min(1.0, (profit_factor or 0) / 2.0)
    return round(score, 4)


def alpha_score_from_backtest_metrics(metrics: Dict[str, Any]) -> float:
    """从 backtest-engine 输出的 metrics 计算 Alpha 分."""
    return alpha_score(
        sharpe_ratio=metrics.get("sharpe_ratio"),
        sortino_ratio=metrics.get("sortino_ratio"),
        max_drawdown=metrics.get("max_drawdown"),
        win_rate_pct=metrics.get("win_rate_pct"),
        profit_factor=metrics.get("profit_factor"),
        total_return=metrics.get("total_return"),
    )


def passes_alpha_threshold(score: float, threshold: float = 0.5) -> bool:
    """是否达到入池阈值."""
    return score >= threshold
