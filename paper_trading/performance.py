# -*- coding: utf-8 -*-
"""
绩效统计：收益率、夏普比率、最大回撤、资金曲线 DataFrame。
"""
from __future__ import annotations
from typing import Optional
import pandas as pd
import numpy as np

from .account import Account


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    if b == 0 or b != b:
        return default
    return a / b


class Performance:
    """
    绩效计算。
    - 收益率（总 / 年化）
    - 夏普比率
    - 最大回撤
    - 资金曲线 DataFrame
    """

    def __init__(self, account: Account):
        self.account = account

    @property
    def total_return(self) -> float:
        """总收益率（小数）。"""
        return self.account.profit_ratio

    @property
    def max_drawdown(self) -> float:
        """最大回撤（小数）。"""
        return self.account.max_drawdown

    def sharpe_ratio(
        self,
        risk_free_rate: float = 0.03,
        periods_per_year: float = 252.0,
    ) -> float:
        """
        夏普比率（年化）。
        :param risk_free_rate: 年化无风险利率
        :param periods_per_year: 年化周期数（日线 252）
        """
        eq = self.equity_curve_df()
        if eq is None or len(eq) < 2:
            return 0.0
        if "return" not in eq.columns:
            eq = eq.copy()
            eq["return"] = eq["equity"].pct_change().fillna(0)
        rf_daily = risk_free_rate / periods_per_year
        excess = eq["return"] - rf_daily
        std_val = excess.std()
        if std_val == 0 or std_val != std_val:
            return 0.0
        return float(np.sqrt(periods_per_year) * excess.mean() / std_val)

    def equity_curve_df(self) -> Optional[pd.DataFrame]:
        """资金曲线 DataFrame：date, equity, return。"""
        if not self.account.equity_curve:
            return None
        rows = [{"date": d, "equity": e} for d, e in self.account.equity_curve]
        df = pd.DataFrame(rows)
        df["return"] = df["equity"].pct_change().fillna(0)
        return df

    def summary(self) -> dict:
        """汇总指标。"""
        return {
            "initial_cash": self.account.initial_cash,
            "total_equity": self.account.total_equity,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio(),
            "trade_count": len(self.account.trades),
        }
