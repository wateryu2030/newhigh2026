# -*- coding: utf-8 -*-
"""
组合生成器：整合策略信号、资金权重、风控，输出最终持仓。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from .risk_budget_engine import get_position_limit, apply_regime_cap
from .risk_controller import RiskController


def build_portfolio(
    candidates: List[Dict[str, Any]],
    strategy_weights: Dict[str, float],
    capital_weights: Dict[str, float],
    total_asset: float,
    prices: Dict[str, float],
    regime: str,
    risk_controller: RiskController,
    max_stocks: int = 10,
    max_weight_per_stock: float = 0.20,
) -> List[Dict[str, Any]]:
    """
    根据候选池、策略权重、资金权重、总资产、价格、市场状态与风控，生成最终持仓列表。
    返回: [{"symbol", "side", "qty", "weight", "reason"}, ...]
    """
    portfolio: List[Dict[str, Any]] = []
    buy_candidates = [c for c in candidates if (c.get("signal") or "").lower() == "buy"]
    buy_candidates.sort(key=lambda x: float(x.get("confidence", 0)), reverse=True)
    buy_candidates = buy_candidates[:max_stocks]
    position_limit = get_position_limit(regime)
    budget = total_asset * position_limit
    for c in buy_candidates:
        sym = c.get("symbol")
        if not sym or sym not in prices or prices[sym] <= 0:
            continue
        conf = float(c.get("confidence", 0.5))
        strategies_in = c.get("strategies", [])
        cap_w = sum(capital_weights.get(s, 0) for s in strategies_in) or (1.0 / max(1, len(strategies_in)))
        target_weight = min(max_weight_per_stock, cap_w * conf * 1.5)
        target_value = apply_regime_cap(total_asset, budget * target_weight, regime)
        qty = int(target_value / prices[sym]) // 100 * 100
        if qty < 100:
            continue
        ok, _ = risk_controller.approve_trade(
            sym,
            "BUY",
            {"total_asset": total_asset, "peak_asset": total_asset, "daily_pnl": 0, "positions": {}},
        )
        if not ok:
            continue
        portfolio.append({
            "symbol": sym,
            "side": "buy",
            "qty": qty,
            "weight": round(target_value / total_asset, 4),
            "reason": f"conf={conf:.2f} strategies={strategies_in}",
        })
    return portfolio
