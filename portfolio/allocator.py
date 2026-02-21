# -*- coding: utf-8 -*-
"""
资金分配器（机构级）：allocate(capital, signals) -> positions。
支持：等权、风险平价、波动率目标、Kelly 简化。
"""
from __future__ import annotations
from typing import Dict, List, Optional, Union
import numpy as np
import pandas as pd


def allocate(
    capital: float,
    signals: Union[pd.DataFrame, Dict[str, float]],
    method: str = "equal",
    volatilities: Optional[Dict[str, float]] = None,
    target_vol: Optional[float] = None,
    kelly_fraction: float = 0.25,
) -> Dict[str, float]:
    """
    将资金按信号与规则分配到各标的。
    :param capital: 总资金
    :param signals: 列含 symbol, weight 或 score；或 { symbol: weight/score }
    :param method: equal | risk_parity | vol_target | kelly
    :param volatilities: 各标的波动率（年化），risk_parity/vol_target 时用
    :param target_vol: 目标组合波动率（vol_target 时用）
    :param kelly_fraction: Kelly 系数（0~1），kelly 时用
    :return: { symbol: 分配金额 }
    """
    if capital <= 0:
        return {}
    sym_weights = _signals_to_weights(signals)
    if not sym_weights:
        return {}
    symbols = list(sym_weights.keys())
    w = np.array([sym_weights[s] for s in symbols], dtype=float)
    w = np.maximum(w, 0)
    if w.sum() <= 0:
        w = np.ones(len(symbols)) / len(symbols)
    if method == "risk_parity" and volatilities:
        inv_vol = np.array([1.0 / max(volatilities.get(s, 1e-6), 1e-6) for s in symbols])
        inv_vol = np.where(np.isfinite(inv_vol), inv_vol, 0)
        if inv_vol.sum() > 0:
            w = inv_vol / inv_vol.sum()
    elif method == "vol_target" and volatilities and target_vol is not None and target_vol > 0:
        vols = np.array([max(volatilities.get(s, 1e-6), 1e-6) for s in symbols])
        # 组合波动率 ≈ w @ vols（简化，无相关矩阵时）
        scale = target_vol / max((w * vols).sum(), 1e-6)
        w = w * min(scale, 3.0)
        w = w / w.sum()
    elif method == "kelly":
        # 简化 Kelly：按 score 当作“胜率/赔率”代理，用 fraction 缩放
        w = w * kelly_fraction + (1 - kelly_fraction) / len(w)
        w = w / w.sum()
    else:
        w = w / w.sum()
    return {s: float(capital * w[i]) for i, s in enumerate(symbols)}


def _signals_to_weights(signals: Union[pd.DataFrame, Dict[str, float]]) -> Dict[str, float]:
    if isinstance(signals, dict):
        return {k: float(v) for k, v in signals.items() if v is not None}
    if isinstance(signals, pd.DataFrame):
        if "symbol" not in signals.columns:
            return {}
        col = "weight" if "weight" in signals.columns else "score"
        if col not in signals.columns:
            col = signals.columns[1] if len(signals.columns) > 1 else None
        if col is None:
            return {}
        return dict(zip(signals["symbol"].astype(str), signals[col].astype(float)))
    return {}
