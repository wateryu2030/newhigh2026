"""
AI 自进化引擎：根据策略收益 vs 市场收益自动调权重/淘汰策略。
逻辑：strategy_return < market_return → reduce_weight；否则 increase_weight。
"""
from __future__ import annotations

from typing import Dict, Optional


class SelfEvolutionEngine:
    def __init__(self, conn=None):
        self._connection = conn
        self._weights: Dict[str, float] = {"emotion": 0.4, "fund": 0.4, "trend": 0.2}

    def get_weights(self) -> Dict[str, float]:
        return dict(self._weights)

    def set_weights(self, emotion: float, fund: float, trend: float) -> None:
        t = emotion + fund + trend
        if t <= 0:
            t = 1.0
        self._weights["emotion"] = emotion / t
        self._weights["fund"] = fund / t
        self._weights["trend"] = trend / t

    def get_strategy_return(self, lookback_days: int = 20) -> Optional[float]:
        """策略收益（占位：可从 trade_signals 回测或实盘统计）。"""
        try:
            from data_pipeline.storage.duckdb_manager import get_conn, get_db_path
            import os
            if not os.path.isfile(get_db_path()):
                return None
            conn = get_conn(read_only=True)
            # 占位：无实盘收益表时返回 None
            conn.close()
        except Exception:
            pass
        return None

    def get_market_return(self, lookback_days: int = 20) -> Optional[float]:
        """市场收益（占位：指数或全市场涨跌幅）。"""
        return None

    def step(self, strategy_return: Optional[float] = None, market_return: Optional[float] = None) -> Dict[str, float]:
        """
        根据收益比较调整权重。
        strategy_return < market_return → 降低当前策略权重（这里简化为略降 trend）；
        否则略升 trend。
        """
        if strategy_return is None:
            strategy_return = self.get_strategy_return()
        if market_return is None:
            market_return = self.get_market_return()
        if strategy_return is not None and market_return is not None:
            if strategy_return < market_return:
                self._weights["trend"] = max(0.1, self._weights["trend"] - 0.05)
                self._weights["emotion"] = min(0.5, self._weights["emotion"] + 0.02)
                self._weights["fund"] = min(0.5, self._weights["fund"] + 0.02)
            else:
                self._weights["trend"] = min(0.4, self._weights["trend"] + 0.03)
                self._weights["emotion"] = max(0.3, self._weights["emotion"] - 0.02)
                self._weights["fund"] = max(0.3, self._weights["fund"] - 0.02)
            t = self._weights["emotion"] + self._weights["fund"] + self._weights["trend"]
            self._weights["emotion"] /= t
            self._weights["fund"] /= t
            self._weights["trend"] /= t
        return self.get_weights()


def run_self_evolution() -> dict:
    """入口：执行一步自进化并返回当前权重。"""
    engine = SelfEvolutionEngine()
    weights = engine.step()
    return {"weights": weights}
