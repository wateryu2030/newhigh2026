"""
Alpha Scoring Engine — 评分模型
alpha_score = sharpe + stability + return - drawdown - volatility
Input: backtest results. Output: alpha_score. Top 10% 进入策略池.
"""
from typing import Any, Dict, List, Tuple


def _norm_sharpe(s: float | None) -> float:
    if s is None:
        return 0.0
    return min(1.0, max(0.0, s / 2.0))


def _norm_return(r: float | None) -> float:
    if r is None:
        return 0.0
    return min(1.0, max(0.0, (r + 0.2) / 0.4))


def _penalty_drawdown(d: float | None) -> float:
    if d is None:
        return 0.0
    return min(1.0, (d or 0) / 0.2)


def _penalty_volatility(v: float | None) -> float:
    if v is None:
        return 0.0
    return min(1.0, (v or 0) / 0.5)


def alpha_score(
    sharpe_ratio: float | None = None,
    sortino_ratio: float | None = None,
    total_return: float | None = None,
    max_drawdown: float | None = None,
    volatility: float | None = None,
    stability: float | None = None,
    *,
    weights: Dict[str, float] | None = None,
) -> float:
    """
    alpha_score = sharpe + stability + return - drawdown - volatility
    Normalized so score is in [0, 1] range (higher = better).
    """
    w = weights or {
        "sharpe": 0.25,
        "stability": 0.15,
        "return": 0.25,
        "drawdown": -0.2,
        "volatility": -0.15,
    }
    score = 0.0
    score += w.get("sharpe", 0) * _norm_sharpe(sharpe_ratio or sortino_ratio)
    score += w.get("stability", 0) * (stability if stability is not None else 0.5)
    score += w.get("return", 0) * _norm_return(total_return)
    score += w.get("drawdown", 0) * _penalty_drawdown(max_drawdown)
    score += w.get("volatility", 0) * _penalty_volatility(volatility)
    return round(min(1.0, max(0.0, score)), 4)


def score_backtest_results(metrics: Dict[str, Any]) -> float:
    """Compute alpha_score from backtest metrics dict."""
    return alpha_score(
        sharpe_ratio=metrics.get("sharpe_ratio"),
        sortino_ratio=metrics.get("sortino_ratio"),
        total_return=metrics.get("total_return"),
        max_drawdown=metrics.get("max_drawdown"),
        volatility=metrics.get("volatility"),
        stability=metrics.get("stability"),
    )


def rank_and_select_top(
    strategies_with_metrics: List[Tuple[Any, Dict[str, Any]]],
    top_fraction: float = 0.1,
) -> List[Tuple[Any, float]]:
    """Score each, rank, return top fraction as (strategy, score)."""
    scored = [(s, score_backtest_results(m)) for s, m in strategies_with_metrics]
    scored.sort(key=lambda x: -x[1])
    k = max(1, int(len(scored) * top_fraction))
    return scored[:k]
