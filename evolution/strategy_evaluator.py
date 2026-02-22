# -*- coding: utf-8 -*-
"""
策略评估器：根据净值曲线计算夏普、最大回撤、胜率等，并给出综合得分（基金级）。
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Any, Dict, Optional, Union


class StrategyEvaluator:
    """多维度评估策略表现，输出综合 score 供进化与上线决策。"""

    def __init__(
        self,
        risk_free_rate: float = 0.0,
        sharpe_weight: float = 2.0,
        max_dd_weight: float = -1.0,
        min_trades: int = 5,
    ):
        self.risk_free_rate = risk_free_rate
        self.sharpe_weight = sharpe_weight
        self.max_dd_weight = max_dd_weight
        self.min_trades = min_trades

    def max_drawdown(self, equity: Union[np.ndarray, pd.Series]) -> float:
        """最大回撤 (0~1)。"""
        if hasattr(equity, "values"):
            equity = equity.values
        equity = np.asarray(equity, dtype=float)
        if len(equity) < 2:
            return 0.0
        peak = equity[0]
        max_dd = 0.0
        for v in equity:
            if v > peak:
                peak = v
            dd = (peak - v) / (peak + 1e-12)
            if dd > max_dd:
                max_dd = dd
        return float(max_dd)

    def evaluate(
        self,
        equity: Union[np.ndarray, pd.Series],
        df_with_signals: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """
        评估净值曲线，返回 sharpe, max_dd, win_rate, profit_factor, score 等。
        :param equity: 净值序列
        :param df_with_signals: 可选，含 signal 列时用于计算胜率、盈亏比
        """
        if hasattr(equity, "values"):
            equity = equity.values
        equity = np.asarray(equity, dtype=float)
        if len(equity) < 2:
            return {
                "sharpe": 0.0,
                "max_dd": 0.0,
                "score": -1e9,
                "total_return": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "n_trades": 0,
            }
        returns = np.diff(equity) / (equity[:-1] + 1e-12)
        total_return = (equity[-1] / equity[0]) - 1.0 if equity[0] > 0 else 0.0
        std = np.std(returns)
        sharpe = (np.mean(returns) - self.risk_free_rate / 252) / (std + 1e-9) * np.sqrt(252) if std > 1e-12 else 0.0
        max_dd = self.max_drawdown(equity)

        win_rate = 0.5
        profit_factor = 1.0
        n_trades = 0
        if df_with_signals is not None and "signal" in df_with_signals.columns:
            s = df_with_signals["signal"].fillna(0)
            # 简单统计：信号从 0->1 为买，1->0 或 -1 为卖
            entries = (s.diff() == 1) | (s.diff() == -1)
            n_trades = int(entries.sum())
            if n_trades >= self.min_trades and "close" in df_with_signals.columns:
                rets = df_with_signals["close"].pct_change()
                trade_returns = rets.where(s.shift(1).fillna(0) != 0).dropna()
                wins = trade_returns[trade_returns > 0]
                losses = trade_returns[trade_returns < 0]
                win_rate = len(wins) / (len(wins) + len(losses) + 1e-12)
                gain = wins.sum()
                loss = abs(losses.sum())
                profit_factor = gain / (loss + 1e-12)

        # 综合得分：夏普正向、回撤负向，可加稳定性（收益波动）
        score = self.sharpe_weight * sharpe + self.max_dd_weight * max_dd
        if n_trades < self.min_trades:
            score -= 0.5  # 交易过少惩罚

        return {
            "sharpe": round(float(sharpe), 4),
            "max_dd": round(float(max_dd), 4),
            "score": round(float(score), 4),
            "total_return": round(float(total_return), 4),
            "win_rate": round(float(win_rate), 4),
            "profit_factor": round(float(profit_factor), 4),
            "n_trades": n_trades,
        }
