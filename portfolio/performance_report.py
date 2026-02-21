# -*- coding: utf-8 -*-
"""
组合绩效报告：收益曲线、每日净值、最大回撤、夏普比率、各策略贡献。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def _to_curve_list(curve: Any) -> List[Dict[str, Any]]:
    """标准化为 [{date, value}, ...]。"""
    if curve is None:
        return []
    if isinstance(curve, pd.DataFrame):
        if "date" in curve.columns and "value" in curve.columns:
            return curve[["date", "value"]].to_dict("records")
        if "date" in curve.columns and "close" in curve.columns:
            v0 = float(curve["close"].iloc[0]) if len(curve) > 0 else 1.0
            return [{"date": str(r["date"])[:10], "value": float(r["close"]) / v0} for _, r in curve.iterrows()]
    if isinstance(curve, list) and curve and isinstance(curve[0], dict):
        return curve
    return []


def _daily_returns(curve: List[Dict[str, Any]]) -> List[float]:
    """每日收益率。"""
    if not curve or len(curve) < 2:
        return []
    vals = [p.get("value", 1.0) for p in curve]
    rets = []
    for i in range(1, len(vals)):
        prev = vals[i - 1] or 1.0
        curr = vals[i] or prev
        rets.append((curr - prev) / prev if prev else 0.0)
    return rets


class PerformanceReport:
    """
    自动生成组合绩效报告：
    - 组合收益曲线
    - 每日净值
    - 最大回撤
    - 夏普比率
    - 各策略贡献
    """

    @staticmethod
    def generate(
        curve: Any,
        strategy_curves: Optional[Dict[str, Any]] = None,
        weights: Optional[Dict[str, float]] = None,
        risk_free_rate: float = 0.02,
    ) -> Dict[str, Any]:
        """
        :param curve: 组合净值曲线 [{date, value}, ...]
        :param strategy_curves: { strategy_id: curve }
        :param weights: { strategy_id: weight }
        :param risk_free_rate: 年化无风险利率，用于夏普
        :return: 报告 dict
        """
        c = _to_curve_list(curve)
        if not c:
            return {
                "curve": [],
                "daily_nav": [],
                "total_return": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "strategy_contribution": {},
            }

        vals = [p.get("value", 1.0) for p in c]
        total_return = (vals[-1] - vals[0]) / vals[0] if vals[0] else 0.0

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
                ann_ret = mean_ret * 252
                ann_vol = std_ret * np.sqrt(252)
                sharpe = (ann_ret - risk_free_rate / 252) / ann_vol if ann_vol > 0 else 0.0

        strategy_contrib = {}
        if strategy_curves and weights:
            for sid, sc in strategy_curves.items():
                sc_list = _to_curve_list(sc)
                if not sc_list:
                    continue
                init_val = sc_list[0].get("value", 1.0)
                final_val = sc_list[-1].get("value", 1.0)
                strat_ret = (final_val - init_val) / init_val if init_val else 0.0
                w = weights.get(sid, 0.0)
                strategy_contrib[sid] = {
                    "return": strat_ret,
                    "weight": w,
                    "contribution": strat_ret * w,
                }

        return {
            "curve": c,
            "daily_nav": c,
            "total_return": total_return,
            "max_drawdown": max_dd,
            "sharpe_ratio": round(sharpe, 4),
            "strategy_contribution": strategy_contrib,
            "summary": {
                "total_returns": total_return,
                "return_rate": total_return,
                "max_drawdown": max_dd,
                "sharpe_ratio": round(sharpe, 4),
            },
        }
