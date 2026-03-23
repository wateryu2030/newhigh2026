"""Strategy 数据（当前为 stub，后续接回测/策略引擎）。"""

from __future__ import annotations

from typing import Any, Dict


def get_strategies_summary() -> Dict[str, Any]:
    """策略概览，供 /api/strategies。"""
    return {
        "strategies": [
            {"id": "trend_following", "name": "Trend Following"},
            {"id": "mean_reversion", "name": "Mean Reversion"},
            {"id": "breakout", "name": "Breakout"},
        ]
    }
