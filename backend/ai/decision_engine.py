# -*- coding: utf-8 -*-
"""
决策引擎：整合 AI 预测、市场状态、风控，输出 buy/sell/hold 及仓位比例。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

import pandas as pd

from .market_regime import detect_regime, get_regime_weight, RegimeType
from .portfolio_manager import optimize_weights, MAX_WEIGHT_PER_STOCK, MAX_HOLDINGS
from .risk_controller import RiskController


def run_decision(
    predicted_returns: pd.Series,
    market_df: pd.DataFrame,
    risk_controller: RiskController,
    current_positions: Optional[Dict[str, Any]] = None,
    total_asset: float = 1.0,
    prices: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    生成交易决策列表。
    返回: [{"symbol": str, "action": "buy"|"sell"|"hold", "weight": float, "reason": str}, ...]
    """
    current_positions = current_positions or {}
    prices = prices or {}
    regime = detect_regime(market_df)
    regime_scale = get_regime_weight(regime)
    symbols = risk_controller.filter_blacklist(predicted_returns.index.tolist())
    if not symbols:
        return []
    pred = predicted_returns.reindex(symbols).dropna()
    pred = pred[pred > 0]
    if len(pred) == 0:
        return []
    weights = optimize_weights(
        pred,
        max_weight=MAX_WEIGHT_PER_STOCK,
        max_stocks=MAX_HOLDINGS,
    )
    portfolio = {
        "total_asset": total_asset,
        "peak_asset": total_asset,
        "daily_pnl": 0,
        "positions": current_positions,
    }
    decisions = []
    for sym, w in weights.items():
        w_adj = w * regime_scale
        ok, reason = risk_controller.approve_trade(sym, "BUY", portfolio)
        if not ok:
            decisions.append({"symbol": sym, "action": "hold", "weight": 0.0, "reason": reason})
            continue
        decisions.append({"symbol": sym, "action": "buy", "weight": round(w_adj, 4), "reason": f"regime={regime}"})
    return decisions
