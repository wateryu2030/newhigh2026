# -*- coding: utf-8 -*-
"""
生产级组合分配：信号 + AI 策略权重 → 订单列表（含 weight 供风控）。
"""
from __future__ import annotations
from typing import Any, Dict, List


class ProductionAllocator:
    """
    将策略信号与 AI 权重转为可执行订单。
    signals: [{"symbol", "action", "strategy": "dragon"|"trend"|"mean"}]
    market_data: { "total_asset", "prices": {symbol: price}, "strategy_weights": {dragon, trend, mean, cash} }
    返回: [{"symbol", "qty", "side", "weight", "strategy", ...}]
    """

    def __init__(self, total_asset: float = 1000000.0, max_single_weight: float = 0.2):
        self.total_asset = total_asset
        self.max_single_weight = max_single_weight

    def allocate(self, signals: List[Dict[str, Any]], market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not signals:
            return []
        total_asset = float(market_data.get("total_asset") or self.total_asset)
        prices = market_data.get("prices") or {}
        strategy_weights = market_data.get("strategy_weights") or {"dragon": 0.4, "trend": 0.3, "mean": 0.2, "cash": 0.1}
        orders: List[Dict[str, Any]] = []
        seen: Dict[str, Dict[str, Any]] = {}
        for s in signals:
            symbol = s.get("symbol") or s.get("code")
            if not symbol:
                continue
            action = (s.get("action") or "buy").lower()
            strategy = (s.get("strategy") or "trend").strip().lower()
            w = float(strategy_weights.get(strategy, 0.2))
            w = min(w, self.max_single_weight)
            price = float(prices.get(symbol, 0) or 0)
            if price <= 0:
                continue
            target_value = total_asset * w
            qty = int(target_value / price / 100) * 100 or 100
            key = symbol
            if key in seen:
                existing = seen[key]
                existing["qty"] = existing["qty"] + (qty if action == "buy" else -qty)
                existing["weight"] = min(existing.get("weight", 0) + w, self.max_single_weight)
            else:
                order = {
                    "symbol": symbol,
                    "qty": qty if action == "buy" else -qty,
                    "side": "BUY" if action == "buy" else "SELL",
                    "weight": w,
                    "strategy": strategy,
                    "price": price,
                    "target_value": target_value,
                }
                seen[key] = order
                orders.append(order)
        return [o for o in orders if o.get("qty", 0) != 0]
