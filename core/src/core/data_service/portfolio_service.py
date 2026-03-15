"""Portfolio 数据（当前为 stub，后续接持仓/资金）。"""

from __future__ import annotations

from typing import Any, Dict


def get_portfolio_summary() -> Dict[str, Any]:
    """组合概览，供 /api/portfolio。"""
    return {"weights": {}, "capital": 0}
