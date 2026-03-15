"""
Meta Fund Manager — AI 基金经理大脑
选择策略、分配资金、监控表现、关闭差策略、启动新策略。
"""

from typing import Any, Dict, List, Optional


def select_strategies(
    strategies_with_scores: List[tuple],
    max_strategies: int = 20,
    min_score: float = 0.3,
) -> List[Any]:
    """Select strategies for deployment: top by score, above min_score."""
    sorted_list = sorted(strategies_with_scores, key=lambda x: -x[1])
    selected = [s for s, score in sorted_list if score >= min_score][:max_strategies]
    return selected


def allocate_capital(
    strategies: List[Any],
    total_capital: float,
    method: str = "equal",
    scores: Optional[Dict[int, float]] = None,
) -> Dict[int, float]:
    """
    Allocate capital across strategies. method: equal | risk_parity | kelly | volatility_targeting.
    Returns strategy_index -> amount.
    """
    n = len(strategies)
    if n == 0:
        return {}
    if method == "equal":
        return {i: total_capital / n for i in range(n)}
    if method == "alpha_weighted" and scores:
        total_s = sum(scores.get(i, 0) for i in range(n))
        if total_s <= 0:
            return {i: total_capital / n for i in range(n)}
        return {i: total_capital * scores.get(i, 0) / total_s for i in range(n)}
    return {i: total_capital / n for i in range(n)}


def should_disable(
    strategy_id: str,
    current_drawdown: float,
    current_pnl: float,
    min_score: float = 0.2,
    max_drawdown: float = 0.1,
) -> bool:
    """Decide if strategy should be disabled (poor performance)."""
    if current_drawdown >= max_drawdown:
        return True
    if current_pnl < -0.05:
        return True
    return False


def monitor_performance(
    strategy_results: Dict[str, Dict[str, Any]],
) -> List[str]:
    """Return list of strategy_ids that should be disabled."""
    disabled = []
    for sid, data in strategy_results.items():
        if should_disable(
            sid,
            current_drawdown=data.get("drawdown", 0) or 0,
            current_pnl=data.get("pnl", 0) or 0,
        ):
            disabled.append(sid)
    return disabled
