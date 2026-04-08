# Auto-fixed by Cursor on 2026-04-02: BacktestResult dataclass for API/tests.
"""结构化回测输出，便于 API / 测试断言。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class BacktestResult:
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    total_return: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate_pct: Optional[float] = None
    profit_factor: Optional[float] = None
    total_profit: Optional[float] = None
    trade_count: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "equity_curve": self.equity_curve,
            "total_return": self.total_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate_pct": self.win_rate_pct,
            "profit_factor": self.profit_factor,
            "total_profit": self.total_profit,
            "trade_count": self.trade_count,
            "error": self.error,
            "metadata": self.metadata,
        }
