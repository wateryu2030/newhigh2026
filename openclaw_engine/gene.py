"""
策略基因表示：可序列化的规则树 + 参数，供遗传操作与回测。
"""

from __future__ import annotations

import copy
from typing import Any, Dict


class StrategyGene:
    """策略个体：规则树（信号条件） + 参数（仓位、止盈止损等）。"""

    def __init__(self, rule_tree: Dict[str, Any], params: Dict[str, Any], strategy_id: str = ""):
        self.rule_tree = rule_tree  # 如 {'and': [{'>': ('emotion_cycle', 0.8)}, {'in': ('hotmoney_seat', 'top3')}]}
        self.params = params  # 如 {'position_pct': 0.1, 'stop_loss': 0.05}
        self.strategy_id = strategy_id or ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "rule_tree": copy.deepcopy(self.rule_tree),
            "params": copy.deepcopy(self.params),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "StrategyGene":
        return cls(
            rule_tree=d.get("rule_tree") or {},
            params=d.get("params") or {},
            strategy_id=str(d.get("strategy_id") or ""),
        )

    def copy(self) -> "StrategyGene":
        return StrategyGene(
            copy.deepcopy(self.rule_tree),
            copy.deepcopy(self.params),
            self.strategy_id,
        )
