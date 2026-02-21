# -*- coding: utf-8 -*-
"""
组合系统配置：目标收益 20~40%，风控参数、策略权重等。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RiskConfig:
    """风控配置。"""
    stop_loss_pct: float = 0.08
    max_drawdown_warn: float = 0.10
    max_drawdown_stop: float = 0.15
    position_limit_pct: float = 0.25
    max_position_count: int = 10


@dataclass
class PortfolioConfig:
    """机构级组合配置。目标年化 20~40%。"""
    initial_cash: float = 1_000_000.0
    target_annual_return_min: float = 0.20
    target_annual_return_max: float = 0.40
    risk_config: RiskConfig = field(default_factory=RiskConfig)
    rebalance_freq: str = "monthly"
    index_symbol: str = "000300.XSHG"
    strategy_weights: Optional[Dict[str, float]] = None

    def __post_init__(self) -> None:
        if self.strategy_weights is None:
            self.strategy_weights = {
                "ma_cross": 0.25,
                "rsi": 0.20,
                "macd": 0.25,
                "kdj": 0.15,
                "breakout": 0.15,
            }
