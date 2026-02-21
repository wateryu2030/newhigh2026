# -*- coding: utf-8 -*-
"""
风控模块：单股止损、账户回撤保护、市场风险判断、仓位限制。
"""
from __future__ import annotations
from enum import Enum
from typing import Optional
import pandas as pd


class RiskLevel(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    STOP = "STOP"


class RiskController:
    """
    风控控制器。
    1. 单股止损（默认 8%）
    2. 账户回撤保护：>10% 降仓，>15% 停止
    3. 市场风险：指数跌破 MA20 判定 HIGH
    4. 仓位限制：单股 ≤ 25%，最大持仓数 ≤ 10
    """

    def __init__(
        self,
        stop_loss_pct: float = 0.08,
        max_drawdown_warn: float = 0.10,
        max_drawdown_stop: float = 0.15,
        position_limit_pct: float = 0.25,
        max_position_count: int = 10,
    ) -> None:
        self.stop_loss_pct = stop_loss_pct
        self.max_drawdown_warn = max_drawdown_warn
        self.max_drawdown_stop = max_drawdown_stop
        self.position_limit_pct = position_limit_pct
        self.max_position_count = max_position_count

    def check_stop_loss(self, cost_price: float, current_price: float) -> bool:
        """单股是否触发止损。"""
        if cost_price <= 0:
            return False
        loss = (cost_price - current_price) / cost_price
        return loss >= self.stop_loss_pct

    def check_account_risk(self, max_drawdown: float) -> RiskLevel:
        """根据最大回撤判断账户风险等级。"""
        if max_drawdown >= self.max_drawdown_stop:
            return RiskLevel.STOP
        if max_drawdown >= self.max_drawdown_warn:
            return RiskLevel.HIGH
        if max_drawdown >= self.max_drawdown_warn * 0.5:
            return RiskLevel.NORMAL
        return RiskLevel.LOW

    def check_market_risk(self, index_df: Optional[pd.DataFrame]) -> RiskLevel:
        """指数跌破 MA20 判定市场高风险。"""
        if index_df is None or len(index_df) < 20:
            return RiskLevel.NORMAL
        df = index_df.copy()
        if "close" not in df.columns:
            return RiskLevel.NORMAL
        df["ma20"] = df["close"].rolling(20, min_periods=1).mean()
        latest = df.iloc[-1]
        close = float(latest["close"])
        ma20 = float(latest["ma20"])
        if ma20 <= 0:
            return RiskLevel.NORMAL
        if close < ma20:
            return RiskLevel.HIGH
        return RiskLevel.LOW

    def get_risk_status(
        self,
        max_drawdown: float,
        index_df: Optional[pd.DataFrame] = None,
    ) -> RiskLevel:
        """综合风险状态，取账户与市场较高等级。"""
        acc = self.check_account_risk(max_drawdown)
        if acc == RiskLevel.STOP:
            return RiskLevel.STOP
        mkt = self.check_market_risk(index_df)
        if mkt == RiskLevel.HIGH:
            return RiskLevel.HIGH if acc != RiskLevel.STOP else RiskLevel.STOP
        return acc

    def get_position_scale(self, risk_level: RiskLevel) -> float:
        """根据风险等级返回建议仓位比例。"""
        if risk_level == RiskLevel.STOP:
            return 0.0
        if risk_level == RiskLevel.HIGH:
            return 0.3
        if risk_level == RiskLevel.NORMAL:
            return 0.6
        return 1.0
