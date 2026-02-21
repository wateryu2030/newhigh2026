# -*- coding: utf-8 -*-
"""
绩效报告：机构级指标，目标年化 20~40%。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np


def _to_curve(curve: Any) -> List[Dict[str, Any]]:
    if curve is None:
        return []
    if isinstance(curve, list) and curve and isinstance(curve[0], dict):
        return curve
    return []


def _daily_returns(curve: List[Dict[str, Any]]) -> List[float]:
    if not curve or len(curve) < 2:
        return []
    vals = [p.get("value", 1.0) for p in curve]
    return [
        (vals[i] - vals[i - 1]) / vals[i - 1] if vals[i - 1] else 0.0
        for i in range(1, len(vals))
    ]


class PerformanceReport:
    """
    机构级绩效报告。
    输出：总收益、年化收益、最大回撤、夏普比率、卡玛比率、交易次数。
    """

    @staticmethod
    def generate(
        curve: Any,
        risk_free_rate: float = 0.02,
        trading_days: int = 252,
    ) -> Dict[str, Any]:
        """
        :param curve: [{ date, value }, ...]
        :param risk_free_rate: 年化无风险利率
        :param trading_days: 年化交易日数
        """
        c = _to_curve(curve)
        if not c:
            return {
                "total_return": 0.0,
                "annual_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "calmar_ratio": 0.0,
                "trade_count": 0,
            }
        vals = [p.get("value", 1.0) for p in c]
        total_return = (vals[-1] - vals[0]) / vals[0] if vals[0] else 0.0
        days = len(c)
        annual_return = (1 + total_return) ** (trading_days / max(1, days)) - 1 if days > 0 else 0.0
        peak = vals[0]
        max_dd = 0.0
        for v in vals:
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak
                if dd > max_dd:
                    max_dd = dd
        rets = _daily_returns(c)
        sharpe = 0.0
        if len(rets) > 0:
            mean_ret = np.mean(rets)
            std_ret = np.std(rets)
            if std_ret > 0:
                ann_ret = mean_ret * trading_days
                ann_vol = std_ret * np.sqrt(trading_days)
                sharpe = (ann_ret - risk_free_rate) / ann_vol if ann_vol > 0 else 0.0
        calmar = annual_return / max_dd if max_dd > 0 else 0.0
        return {
            "total_return": round(total_return, 4),
            "annual_return": round(annual_return, 4),
            "max_drawdown": round(max_dd, 4),
            "sharpe_ratio": round(sharpe, 4),
            "calmar_ratio": round(calmar, 4),
            "days": days,
        }
