"""
Strategy Selector — 策略选择系统
AI 自动挑选：哪些策略上线、哪些暂停、哪些淘汰
"""
from typing import List, Optional

from evolution_engine import StrategyPool, StrategyRecord, StrategyStatus


def select_for_live(
    pool: StrategyPool,
    *,
    max_strategies: int = 20,
    min_alpha_score: float = 0.5,
) -> List[StrategyRecord]:
    """
    从 APPROVED 中选出应上实盘的策略（按 Alpha 分排序，取前 max_strategies）。
    """
    approved = pool.list_by_status(StrategyStatus.APPROVED)
    with_score = [(r, r.alpha_score or 0.0) for r in approved]
    with_score.sort(key=lambda x: -x[1])
    return [r for r, _ in with_score[:max_strategies]]


def select_to_suspend(
    pool: StrategyPool,
    strategy_ids: List[str],
) -> List[str]:
    """返回应暂停的策略 ID 列表（由风控或达尔文引擎传入）。"""
    return list(strategy_ids)


def select_to_retire(
    pool: StrategyPool,
    strategy_ids: List[str],
) -> List[str]:
    """返回应淘汰的策略 ID 列表。"""
    return list(strategy_ids)
