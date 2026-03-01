# -*- coding: utf-8 -*-
"""
生产级交易引擎：日频闭环。
run_daily(market_data) → 策略信号 → 组合分配 → 风控过滤 → 券商下单。
目标：100万–1000万资金，年化 20–40%，最大回撤 <15%。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TradingEngine:
    """
    交易引擎：broker + strategies + portfolio + risk 闭环。
    策略返回 [{"symbol": str, "action": "buy"|"sell", "strategy": str}]
    组合输出 [{"symbol", "qty", "side", "weight", ...}]
    风控过滤后送 broker.send_order。
    """

    def __init__(
        self,
        broker: Any,
        strategies: List[Any],
        portfolio: Any,
        risk: Any,
        event_bus: Optional[Any] = None,
    ):
        self.broker = broker
        self.strategies = strategies
        self.portfolio = portfolio
        self.risk = risk
        self.event_bus = event_bus

    def run_daily(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        market_data: { "symbols": {"600519": df, ...}, "index_df": df 可选 }
        返回: { "signals": [], "orders": [], "safe_orders": [], "sent": [] }
        """
        result: Dict[str, Any] = {"signals": [], "orders": [], "safe_orders": [], "sent": []}
        symbols_data = market_data.get("symbols") or market_data.get("symbols_data") or {}

        # 1) 策略信号
        signals: List[Dict[str, Any]] = []
        for name, strategy in self.strategies:
            for code, df in symbols_data.items():
                if df is None or len(df) < 20:
                    continue
                try:
                    out = strategy.generate(df, code=code)
                    if out:
                        for item in out if isinstance(out, list) else [out]:
                            item["strategy"] = name
                            signals.append(item)
                except Exception as e:
                    logger.debug("strategy %s %s: %s", name, code, e)
        result["signals"] = signals

        if self.event_bus:
            self.event_bus.publish("signals", signals)

        # 2) 组合分配 → orders（带 weight）
        orders = self.portfolio.allocate(signals, market_data) if signals else []
        result["orders"] = orders

        # 3) 风控过滤
        safe_orders = self.risk.check(orders) if hasattr(self.risk, "check") else orders
        if not hasattr(self.risk, "check") and hasattr(self.risk, "check_order"):
            safe_orders = []
            for o in orders:
                ok, _ = self.risk.check_order(
                    o.get("symbol", ""),
                    o.get("qty", 0),
                    o.get("side", "BUY"),
                    market_data.get("positions") or {},
                    market_data.get("total_asset") or 1.0,
                )
                if ok:
                    safe_orders.append(o)
        result["safe_orders"] = safe_orders

        if self.event_bus:
            self.event_bus.publish("orders_checked", safe_orders)

        # 4) 下单
        for order in safe_orders:
            try:
                sent = self.broker.send_order(order)
                if sent:
                    result["sent"].append(sent)
            except Exception as e:
                logger.warning("broker send_order failed: %s", e)
        return result
