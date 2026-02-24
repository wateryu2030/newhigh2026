# -*- coding: utf-8 -*-
"""
策略基类：统一接口 generate_signals(data)、score(performance)。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import pandas as pd


class BaseStrategy(ABC):
    """抽象策略：子类实现 generate_signals 与 score。"""

    name: str = "Base"
    strategy_id: str = "base"

    @abstractmethod
    def generate_signals(self, data: Any) -> List[Dict[str, Any]]:
        """
        根据行情数据生成信号。
        data: 可为 Dict[symbol, DataFrame] 或 DataFrame，含 OHLCV。
        返回: [{"symbol": str, "signal": "buy"|"sell"|"hold", "confidence": float in [0,1]}, ...]
        """
        pass

    def score(self, performance: Dict[str, Any]) -> float:
        """
        根据历史表现给策略打分，用于权重分配。
        performance: {"return": float, "sharpe": float, "max_drawdown": float, "win_rate": float, "stability": float}
        返回: 0~1 的分数，越高越优。
        """
        ret = float(performance.get("return", 0) or 0)
        sharpe = float(performance.get("sharpe", 0) or 0)
        max_dd = float(performance.get("max_drawdown", 1) or 1)
        win_rate = float(performance.get("win_rate", 0.5) or 0.5)
        stability = float(performance.get("stability", 0.5) or 0.5)
        if max_dd <= 0:
            max_dd = 1e-6
        score = 0.2 * min(1.0, max(0, ret + 0.2)) + 0.25 * min(1.0, max(0, sharpe + 0.5)) + 0.25 * (1 - min(1.0, max_dd)) + 0.15 * win_rate + 0.15 * stability
        return max(0.0, min(1.0, score))
