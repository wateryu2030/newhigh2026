# -*- coding: utf-8 -*-
"""
策略表现分析：Sharpe、Calmar、WinRate、Volatility。
"""
from __future__ import annotations
from typing import Any, Dict, Union
import numpy as np


class StrategyMetrics:
    def calculate(self, equity: Union[np.ndarray, list]) -> Dict[str, float]:
        if hasattr(equity, "__iter__") and not isinstance(equity, np.ndarray):
            equity = np.asarray(equity, dtype=float)
        if len(equity) < 2:
            return {"sharpe": 0.0, "max_dd": 0.0, "vol": 0.0, "calmar": 0.0}
        returns = np.diff(equity) / (equity[:-1] + 1e-12)
        vol = float(np.std(returns))
        sharpe = float(np.mean(returns) / (vol + 1e-9)) * np.sqrt(252) if vol > 1e-12 else 0.0
        max_dd = self.max_drawdown(equity)
        total_return = (equity[-1] / (equity[0] + 1e-12)) - 1.0
        calmar = total_return / (max_dd + 1e-9) if max_dd > 1e-9 else 0.0
        return {
            "sharpe": round(sharpe, 4),
            "max_dd": round(max_dd, 4),
            "vol": round(vol, 6),
            "calmar": round(calmar, 4),
        }

    def max_drawdown(self, equity: Union[np.ndarray, list]) -> float:
        if hasattr(equity, "__iter__") and not isinstance(equity, np.ndarray):
            equity = np.asarray(equity, dtype=float)
        peak = float(equity[0])
        max_dd = 0.0
        for v in equity:
            peak = max(peak, float(v))
            dd = (peak - v) / (peak + 1e-12)
            max_dd = max(max_dd, dd)
        return float(max_dd)
