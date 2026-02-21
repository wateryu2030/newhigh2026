# -*- coding: utf-8 -*-
"""
策略归因：各策略对组合收益的贡献度。
"""
from __future__ import annotations
from typing import Dict, List, Any


class StrategyAttribution:
    """
    策略归因：计算各策略对组合总收益、回撤的贡献。
    """

    @staticmethod
    def attribution(
        strategy_curves: Dict[str, List[Dict[str, Any]]],
        weights: Dict[str, float],
    ) -> Dict[str, Dict[str, float]]:
        """
        计算各策略贡献。
        :param strategy_curves: { strategy_id: [{ date, value }, ...] }
        :param weights: { strategy_id: weight }
        :return: { strategy_id: { return, contribution, max_drawdown } }
        """
        out = {}
        for sid, curve in strategy_curves.items():
            if not curve:
                out[sid] = {"return": 0.0, "contribution": 0.0, "max_drawdown": 0.0}
                continue
            init_val = curve[0].get("value", 1.0)
            final_val = curve[-1].get("value", 1.0)
            ret = (final_val - init_val) / init_val if init_val else 0.0
            w = weights.get(sid, 0.0)
            contrib = ret * w
            peak = init_val
            max_dd = 0.0
            for p in curve:
                v = p.get("value", init_val)
                if v > peak:
                    peak = v
                if peak > 0:
                    dd = (peak - v) / peak
                    if dd > max_dd:
                        max_dd = dd
            out[sid] = {"return": ret, "contribution": contrib, "max_drawdown": max_dd}
        return out
