# -*- coding: utf-8 -*-
"""
机构级组合引擎：数据 → 多策略 → 合并信号 → 分配资金 → 风控 → 交易指令。
复用 strategies_pro.StrategyManager、portfolio.allocator、risk.RiskEngine。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd


class InstitutionalPortfolioEngine:
    """
    流程：数据 → 多策略信号 → 合并 → 资金分配 → 仓位约束 → 风控缩放 → 输出目标仓位/指令。
    """

    def __init__(
        self,
        capital: float = 1_000_000,
        allocator_method: str = "equal",
        max_drawdown_warn: float = 0.10,
        max_drawdown_stop: float = 0.15,
        max_single_pct: float = 0.10,
        max_sector_pct: float = 0.30,
        max_positions: int = 15,
    ):
        self.capital = capital
        self.allocator_method = allocator_method
        self.max_drawdown_warn = max_drawdown_warn
        self.max_drawdown_stop = max_drawdown_stop
        self.max_single_pct = max_single_pct
        self.max_sector_pct = max_sector_pct
        self.max_positions = max_positions

    def run(
        self,
        market_data: Dict[str, pd.DataFrame],
        index_df: Optional[pd.DataFrame] = None,
        current_max_drawdown: float = 0.0,
        sector_map: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        执行一轮：多策略 → 合并 → 分配 → 风控 → 目标仓位。
        :param market_data: 多标的 K 线
        :param index_df: 指数 K 线（可选，用于市场状态）
        :param current_max_drawdown: 当前账户最大回撤 (0~1)
        :param sector_map: symbol -> 行业，用于行业约束
        :return: { "orders": [], "target_positions": { symbol: value }, "risk_scale": float, "signals": df }
        """
        try:
            from strategies_pro import StrategyManager
        except Exception:
            return self._empty_result()
        from portfolio.allocator import allocate
        from portfolio.position_manager import PositionManager
        from risk.risk_engine import RiskEngine

        manager = StrategyManager()
        if index_df is not None and len(index_df) >= 60:
            manager.set_index_data(index_df)
        combined = manager.get_combined_signals(market_data)
        if combined is None or len(combined) == 0:
            return self._empty_result()

        # 合并为 symbol -> weight（按 strategy 聚合或取平均）
        if "symbol" in combined.columns and "weight" in combined.columns:
            sig = combined.groupby("symbol", as_index=False)["weight"].sum()
            signals = dict(zip(sig["symbol"].astype(str), sig["weight"].astype(float)))
        else:
            signals = {}
        if not signals:
            return self._empty_result()

        risk_engine = RiskEngine(
            max_drawdown_warn=self.max_drawdown_warn,
            max_drawdown_stop=self.max_drawdown_stop,
        )
        scale = risk_engine.apply_drawdown_rules(current_max_drawdown)
        capital_eff = self.capital * scale

        positions = allocate(capital_eff, signals, method=self.allocator_method)
        pos_mgr = PositionManager(
            max_single_pct=self.max_single_pct,
            max_sector_pct=self.max_sector_pct,
            max_positions=self.max_positions,
            sector_map=sector_map or {},
        )
        target_positions = pos_mgr.apply_constraints(positions, capital_eff)

        orders = [
            {"symbol": s, "value": v, "side": "BUY"}
            for s, v in target_positions.items()
            if v > 0
        ]
        return {
            "orders": orders,
            "target_positions": target_positions,
            "risk_scale": scale,
            "signals": combined,
        }

    def _empty_result(self) -> Dict[str, Any]:
        return {
            "orders": [],
            "target_positions": {},
            "risk_scale": 1.0,
            "signals": pd.DataFrame(),
        }
