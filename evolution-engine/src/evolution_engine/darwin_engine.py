"""
Strategy Darwin Engine — 策略达尔文淘汰系统
持续评估实盘表现，淘汰劣质策略、保留/进化优质策略
"""

from datetime import datetime, timedelta
from typing import Callable, List, Optional

from .strategy_pool import StrategyPool, StrategyRecord, StrategyStatus
from .alpha_scoring import alpha_score_from_backtest_metrics


def should_retire(
    record: StrategyRecord,
    *,
    min_alpha_score: float = 0.3,
    max_drawdown: Optional[float] = None,
    min_live_days: int = 7,
) -> bool:
    """
    是否应淘汰该策略：
    - Alpha 分低于阈值
    - 回撤超限（若提供 backtest_metrics）
    - 实盘时间过短则不轻易淘汰（可选）
    """
    if record.status != StrategyStatus.LIVE and record.status != StrategyStatus.SUSPENDED:
        return False
    if record.alpha_score is not None and record.alpha_score < min_alpha_score:
        return True
    if max_drawdown is not None and record.backtest_metrics:
        md = record.backtest_metrics.get("max_drawdown")
        if md is not None and md > max_drawdown:
            return True
    return False


def should_suspend(
    record: StrategyRecord,
    *,
    current_drawdown: Optional[float] = None,
    drawdown_limit: float = 0.1,
) -> bool:
    """是否应暂停（风控触发后由 risk-engine 调用）。"""
    if record.status != StrategyStatus.LIVE:
        return False
    if current_drawdown is not None and current_drawdown >= drawdown_limit:
        return True
    return False


def evolve_pool(
    pool: StrategyPool,
    *,
    min_alpha_to_approve: float = 0.5,
    retire_below_alpha: float = 0.3,
    on_retire: Optional[Callable[[StrategyRecord], None]] = None,
    on_approve: Optional[Callable[[StrategyRecord], None]] = None,
) -> List[str]:
    """
    执行一轮进化：
    - BACKTESTED → 按 Alpha 分 APPROVED 或丢弃
    - LIVE/SUSPENDED → 按规则 RETIRED
    返回本轮被淘汰的 strategy_id 列表
    """
    retired: List[str] = []
    for r in pool.list_by_status(StrategyStatus.BACKTESTED):
        score = r.alpha_score
        if score is None and r.backtest_metrics:
            score = alpha_score_from_backtest_metrics(r.backtest_metrics)
            pool.update_alpha_score(r.id, score)
        if score is not None and score >= min_alpha_to_approve:
            pool.update_status(r.id, StrategyStatus.APPROVED)
            if on_approve:
                on_approve(r)
        # 不达标可保留为 candidate 或丢弃，此处简化为不自动改 status
    for r in pool.list_live() + pool.list_by_status(StrategyStatus.SUSPENDED):
        if should_retire(r, min_alpha_score=retire_below_alpha):
            pool.update_status(r.id, StrategyStatus.RETIRED)
            retired.append(r.id)
            if on_retire:
                on_retire(r)
    return retired
