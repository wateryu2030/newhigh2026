# -*- coding: utf-8 -*-
"""
策略管理器：加载所有策略、收集信号、统一输出候选股票池。
"""
from __future__ import annotations
from typing import Any, Dict, List

from .strategies import (
    TrendStrategy,
    MeanReversionStrategy,
    MomentumStrategy,
    HotSectorStrategy,
    AIMLStrategy,
)
from .strategies.base_strategy import BaseStrategy


# 默认策略列表
DEFAULT_STRATEGIES: List[BaseStrategy] = [
    TrendStrategy(),
    MeanReversionStrategy(),
    MomentumStrategy(),
    HotSectorStrategy(),
    AIMLStrategy(),
]


class StrategyManager:
    """加载策略、运行信号、汇总候选池。"""

    def __init__(self, strategies: List[BaseStrategy] | None = None):
        self.strategies = strategies or DEFAULT_STRATEGIES

    def collect_signals(self, data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        各策略对同一批 data 生成信号。
        data: Dict[symbol, DataFrame] 日线。
        返回: {strategy_id: [{"symbol", "signal", "confidence"}, ...]}
        """
        result: Dict[str, List[Dict[str, Any]]] = {}
        for s in self.strategies:
            try:
                sigs = s.generate_signals(data)
                result[s.strategy_id] = sigs if sigs else []
            except Exception:
                result[s.strategy_id] = []
        return result

    def get_candidate_pool(
        self,
        signals_by_strategy: Dict[str, List[Dict[str, Any]]],
        min_confidence: float = 0.5,
        min_strategies_buy: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        汇总多策略信号为候选池。
        规则：某标的在至少 min_strategies_buy 个策略中为 buy，且平均 confidence >= min_confidence。
        返回: [{"symbol", "signal", "confidence", "strategies": [str]}, ...]
        """
        from collections import defaultdict
        by_symbol: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"buys": 0, "sells": 0, "confs": [], "strategy_ids": []})
        for sid, sigs in signals_by_strategy.items():
            for s in sigs:
                sym = s.get("symbol")
                if not sym:
                    continue
                sig = (s.get("signal") or "hold").lower()
                conf = float(s.get("confidence", 0.5))
                by_symbol[sym]["confs"].append(conf)
                by_symbol[sym]["strategy_ids"].append(sid)
                if sig == "buy":
                    by_symbol[sym]["buys"] += 1
                elif sig == "sell":
                    by_symbol[sym]["sells"] += 1
        out = []
        for sym, v in by_symbol.items():
            buys = v["buys"]
            confs = v["confs"]
            avg_conf = sum(confs) / len(confs) if confs else 0.5
            if buys >= min_strategies_buy and avg_conf >= min_confidence:
                out.append({
                    "symbol": sym,
                    "signal": "buy",
                    "confidence": round(avg_conf, 4),
                    "strategies": list(set(v["strategy_ids"])),
                })
            elif v["sells"] >= min_strategies_buy:
                out.append({
                    "symbol": sym,
                    "signal": "sell",
                    "confidence": round(avg_conf, 4),
                    "strategies": list(set(v["strategy_ids"])),
                })
        return out
