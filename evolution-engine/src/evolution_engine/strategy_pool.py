"""
Strategy Pool — 策略池
策略生命周期：candidate → backtested → approved → live → suspended → retired
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class StrategyStatus(str, Enum):
    CANDIDATE = "candidate"  # AI 生成，待回测
    BACKTESTED = "backtested"  # 已回测，待评分
    APPROVED = "approved"  # Alpha 达标，待上线
    LIVE = "live"  # 实盘运行
    SUSPENDED = "suspended"  # 暂停（风控/回撤）
    RETIRED = "retired"  # 淘汰


@dataclass
class StrategyRecord:
    id: str
    name: str
    strategy_type: str
    params: Dict[str, Any]
    symbols: List[str]
    status: StrategyStatus = StrategyStatus.CANDIDATE
    alpha_score: Optional[float] = None
    backtest_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    live_pnl: Optional[float] = None


class StrategyPool:
    """In-memory strategy pool. Replace with Postgres/Redis for production."""

    def __init__(self) -> None:
        self._records: Dict[str, StrategyRecord] = {}

    def add(self, record: StrategyRecord) -> None:
        record.updated_at = datetime.now(timezone.utc)
        self._records[record.id] = record

    def get(self, strategy_id: str) -> Optional[StrategyRecord]:
        return self._records.get(strategy_id)

    def update_status(self, strategy_id: str, status: StrategyStatus) -> bool:
        r = self._records.get(strategy_id)
        if not r:
            return False
        r.status = status
        r.updated_at = datetime.now(timezone.utc)
        return True

    def update_alpha_score(self, strategy_id: str, score: float) -> bool:
        r = self._records.get(strategy_id)
        if not r:
            return False
        r.alpha_score = score
        r.updated_at = datetime.now(timezone.utc)
        return True

    def update_backtest_metrics(self, strategy_id: str, metrics: Dict[str, Any]) -> bool:
        r = self._records.get(strategy_id)
        if not r:
            return False
        r.backtest_metrics = metrics
        r.status = StrategyStatus.BACKTESTED
        r.updated_at = datetime.now(timezone.utc)
        return True

    def list_by_status(self, status: StrategyStatus) -> List[StrategyRecord]:
        return [r for r in self._records.values() if r.status == status]

    def list_live(self) -> List[StrategyRecord]:
        return self.list_by_status(StrategyStatus.LIVE)

    def list_candidates(self) -> List[StrategyRecord]:
        return self.list_by_status(StrategyStatus.CANDIDATE)
