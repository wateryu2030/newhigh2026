"""
Capital Allocator — 资金配置系统
AI 自动分配资金：按策略 Alpha 分/风险分配 capital
"""

from typing import Dict, List, Optional

from evolution_engine import StrategyPool, StrategyRecord, StrategyStatus


def allocate_capital(
    pool: StrategyPool,
    total_capital: float,
    *,
    live_strategies: Optional[List[StrategyRecord]] = None,
    method: str = "equal",  # equal | alpha_weighted | risk_parity
) -> Dict[str, float]:
    """
    为每个实盘策略分配资金（strategy_id -> 分配金额）。
    equal: 均分
    alpha_weighted: 按 Alpha 分加权
    """
    strategies = live_strategies or pool.list_live()
    if not strategies:
        return {}
    n = len(strategies)
    if method == "equal":
        per = total_capital / n
        return {r.id: per for r in strategies}
    if method == "alpha_weighted":
        scores = [r.alpha_score or 0.0 for r in strategies]
        total_s = sum(scores)
        if total_s <= 0:
            return {r.id: total_capital / n for r in strategies}
        return {r.id: total_capital * (r.alpha_score or 0.0) / total_s for r in strategies}
    # default equal
    per = total_capital / n
    return {r.id: per for r in strategies}


def rebalance_signals(
    current_alloc: Dict[str, float],
    target_alloc: Dict[str, float],
) -> Dict[str, float]:
    """当前分配 -> 目标分配，返回各策略应调整的 delta（正=加仓，负=减仓）。"""
    all_ids = set(current_alloc) | set(target_alloc)
    return {sid: target_alloc.get(sid, 0.0) - current_alloc.get(sid, 0.0) for sid in all_ids}
