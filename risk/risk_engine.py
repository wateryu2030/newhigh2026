# -*- coding: utf-8 -*-
"""
风控引擎：单股止损、账户回撤保护、市场风险判断。
"""
from __future__ import annotations
from enum import Enum
from typing import Dict, Optional
import pandas as pd


class RiskLevel(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    STOP = "STOP"


class RiskEngine:
    """
    风控引擎。
    1. 单股止损规则（默认 8%，可配置）
    2. 账户风险控制：最大回撤 >10% 降仓，>15% 停止交易
    3. 市场风险判断：指数跌破 MA20 判定高风险
    """

    def __init__(
        self,
        stop_loss_pct: float = 0.08,
        max_drawdown_warn: float = 0.10,
        max_drawdown_stop: float = 0.15,
    ):
        self.stop_loss_pct = stop_loss_pct
        self.max_drawdown_warn = max_drawdown_warn
        self.max_drawdown_stop = max_drawdown_stop

    def check_stop_loss(
        self,
        cost_price: float,
        current_price: float,
    ) -> bool:
        """单股是否触发止损。"""
        if cost_price <= 0:
            return False
        loss = (cost_price - current_price) / cost_price
        return loss >= self.stop_loss_pct

    def check_account_risk(
        self,
        max_drawdown: float,
    ) -> RiskLevel:
        """
        根据账户最大回撤判断风险等级。
        - LOW: < 10%
        - NORMAL: 10% ~ 15%
        - HIGH: 10%~15% 降仓
        - STOP: > 15% 停止交易
        """
        if max_drawdown >= self.max_drawdown_stop:
            return RiskLevel.STOP
        if max_drawdown >= self.max_drawdown_warn:
            return RiskLevel.HIGH
        if max_drawdown >= self.max_drawdown_warn * 0.5:
            return RiskLevel.NORMAL
        return RiskLevel.LOW

    def check_market_risk(
        self,
        index_df: pd.DataFrame,
    ) -> RiskLevel:
        """
        使用指数数据判断市场风险。
        指数跌破 MA20 判定 HIGH。
        需至少 20 根 K 线。
        """
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
        """
        综合风险状态。
        取账户风险与市场风险的较高等级。
        """
        acc = self.check_account_risk(max_drawdown)
        if acc == RiskLevel.STOP:
            return RiskLevel.STOP
        mk = self.check_market_risk(index_df) if index_df is not None else RiskLevel.NORMAL
        order = [RiskLevel.LOW, RiskLevel.NORMAL, RiskLevel.HIGH, RiskLevel.STOP]
        ai = order.index(acc)
        mi = order.index(mk)
        return order[max(ai, mi)]

    def apply_drawdown_rules(self, max_drawdown: float) -> float:
        """
        按回撤规则返回仓位缩放系数 (0~1)。
        - 回撤 >= 15%: 清仓，scale=0
        - 回撤 >= 10%: 降仓 30%，scale=0.7
        - 否则: scale=1
        """
        if max_drawdown >= self.max_drawdown_stop:
            return 0.0
        if max_drawdown >= self.max_drawdown_warn:
            return 0.7
        return 1.0

    def check_sector_concentration(
        self,
        positions: Dict[str, float],
        sector_map: Dict[str, str],
        max_sector_pct: float = 0.30,
    ) -> bool:
        """检查行业集中度是否超过 max_sector_pct。"""
        if not positions or not sector_map:
            return True
        total = sum(positions.values())
        if total <= 0:
            return True
        sector_totals: Dict[str, float] = {}
        for sym, val in positions.items():
            sec = sector_map.get(sym, "OTHER")
            sector_totals[sec] = sector_totals.get(sec, 0) + val
        return all(v / total <= max_sector_pct for v in sector_totals.values())

    def check_single_stock_risk(
        self,
        positions: Dict[str, float],
        total_equity: float,
        max_single_pct: float = 0.10,
    ) -> bool:
        """检查单股仓位是否均不超过 max_single_pct。"""
        if total_equity <= 0 or not positions:
            return True
        return all(v / total_equity <= max_single_pct for v in positions.values())
