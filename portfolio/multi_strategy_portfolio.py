# -*- coding: utf-8 -*-
"""
多策略组合系统：主编排。
支持多策略、多标的、权重分配、再平衡、与 paper_trading/risk 集成。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from .capital_allocator import CapitalAllocator
from .portfolio import aggregate_curves
from .strategy_pool import StrategyPool


@dataclass
class StrategyConfig:
    """单个策略配置。"""
    strategy_id: str
    symbol: str
    weight: float = 0.0
    strategy_instance: Any = None  # 可传入已实例化的策略


@dataclass
class PortfolioConfig:
    """组合配置。"""
    strategies: List[StrategyConfig]
    initial_cash: float = 1_000_000.0
    rebalance_freq: str = "monthly"  # daily | weekly | monthly | none
    risk_level: str = "NORMAL"  # LOW | NORMAL | HIGH


class MultiStrategyPortfolio:
    """
    多策略组合主编排。
    - 多策略、多标的
    - 权重分配（等权/自定义/风险平价）
    - 定期再平衡
    - 与 paper_trading 模拟执行对接
    - 策略归因（各策略贡献度）
    """

    def __init__(
        self,
        config: Optional[PortfolioConfig] = None,
        allocator: Optional[CapitalAllocator] = None,
    ):
        self.config = config or PortfolioConfig(strategies=[])
        self.allocator = allocator or CapitalAllocator()
        self._equity_curve: List[Dict[str, Any]] = []
        self._strategy_curves: Dict[str, List[Dict[str, Any]]] = {}

    def add_strategy(self, strategy_id: str, symbol: str, weight: float = 0.0) -> "MultiStrategyPortfolio":
        """动态添加策略配置。"""
        self.config.strategies.append(
            StrategyConfig(strategy_id=strategy_id, symbol=symbol, weight=weight)
        )
        return self

    def _normalize_weights(self) -> List[float]:
        """归一化策略权重。"""
        w = [s.weight for s in self.config.strategies]
        if not w or sum(w) <= 0:
            return [1.0 / len(self.config.strategies)] * len(self.config.strategies)
        s = sum(w)
        return [x / s for x in w]

    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        timeframe: str = "D",
        run_plugin: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        运行多策略组合回测。
        :param run_plugin: (strategy_id, symbol, start, end, tf) -> result
        """
        if not self.config.strategies:
            return {"error": "策略列表为空", "curve": [], "holdCurve": [], "strategy_curves": {}}

        from portfolio import run_portfolio_backtest

        weights = self._normalize_weights()
        strategies_json = [
            {"strategy_id": s.strategy_id, "weight": weights[i], "symbol": s.symbol}
            for i, s in enumerate(self.config.strategies)
        ]
        stock_code = self.config.strategies[0].symbol
        result = run_portfolio_backtest(
            strategies=strategies_json,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            timeframe=timeframe,
        )
        if result.get("error"):
            return result

        self._equity_curve = result.get("curve") or []
        self._strategy_curves = {}
        result["portfolio_config"] = {
            "strategies": [
                {"id": s.strategy_id, "symbol": s.symbol, "weight": w}
                for s, w in zip(self.config.strategies, weights)
            ],
        }
        result["initial_cash"] = self.config.initial_cash
        return result

    def run_with_paper_trading(
        self,
        start_date: str,
        end_date: str,
        load_kline_fn: Optional[Callable[[str, str, str], pd.DataFrame]] = None,
    ) -> Dict[str, Any]:
        """
        使用 paper_trading 模拟执行多策略组合。
        每个策略子账户独立运行，最后按权重合并净值。
        """
        from paper_trading import PaperBroker, TradeEngine, Performance
        from strategies import get_plugin_strategy
        from data.data_loader import load_kline as _load_kline

        def _default_load(sym: str, start: str, end: str):
            df = _load_kline(sym, start, end, source="akshare")
            if df is None or len(df) < 20:
                df = _load_kline(sym, start, end, source="database")
            return df

        load_fn = load_kline_fn or _default_load
        weights = self._normalize_weights()
        curves = []
        perf_list = []
        strategy_names = []

        for i, cfg in enumerate(self.config.strategies):
            strategy = cfg.strategy_instance or get_plugin_strategy(cfg.strategy_id)
            if strategy is None:
                continue
            sym = cfg.symbol.split(".")[0] if "." in cfg.symbol else cfg.symbol
            df = load_fn(sym, start_date, end_date)
            if df is None or len(df) < 20:
                continue

            broker = PaperBroker(initial_cash=self.config.initial_cash * weights[i])
            engine = TradeEngine(broker=broker)

            def _get_sigs(d):
                return strategy.generate_signals(d)

            order_book = sym + ".XSHG" if sym.startswith("6") else sym + ".XSHE"
            engine.run_from_kline(df, order_book, _get_sigs)

            eq = [(d, e) for d, e in broker.account.equity_curve]
            curve = [{"date": d, "value": e / (self.config.initial_cash * weights[i])} for d, e in eq]
            curves.append(curve)
            perf_list.append(Performance(broker.account).summary())
            strategy_names.append(cfg.strategy_id)

        if not curves:
            return {"error": "无有效策略结果", "curve": [], "stats": {}}

        combined = aggregate_curves(curves, weights[: len(curves)])
        final_nav = combined[-1]["value"] if combined else 1.0
        peak = 1.0
        max_dd = 0.0
        for p in combined:
            v = p["value"]
            if v > peak:
                peak = v
            if peak > 0:
                dd = (peak - v) / peak
                if dd > max_dd:
                    max_dd = dd

        self._equity_curve = combined
        self._strategy_curves = {n: c for n, c in zip(strategy_names, curves)}

        return {
            "curve": combined,
            "holdCurve": combined,
            "summary": {
                "total_returns": final_nav - 1.0,
                "return_rate": final_nav - 1.0,
                "max_drawdown": max_dd,
            },
            "stats": {
                "total_return": final_nav - 1.0,
                "max_drawdown": max_dd,
                "tradeCount": sum(p.get("trade_count", 0) for p in perf_list),
            },
            "strategy_performance": perf_list,
            "strategy_names": strategy_names,
        }
