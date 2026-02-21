# -*- coding: utf-8 -*-
"""
投资组合管理：多策略组合执行与持仓追踪。
- PortfolioManager: 多策略组合管理核心（信号聚合、权重分配、回测、paper_trading 对接）
- PositionTracker: 按标的维护持仓市值，汇总总资产（供 monitor API）
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional, Union
import pandas as pd

from .base_strategy import PortfolioStrategyBase, StrategyAdapter
from .signal_aggregator import SignalAggregator, AggregatorConfig
from .weight_allocator import WeightAllocator
from .performance_report import PerformanceReport
from .portfolio import aggregate_curves
from .rebalancer import PortfolioRebalancer


class PositionTracker:
    """
    持仓追踪器：维护 code -> 持仓价值，汇总总资产。
    可与实盘/模拟盘对接，供 monitor API 使用。
    """

    def __init__(self, capital: float = 0.0):
        self.capital = capital
        self.positions: Dict[str, float] = {}

    def update(self, code: str, value: float) -> None:
        self.positions[code] = value

    def get(self, code: str) -> float:
        return self.positions.get(code, 0.0)

    def total_value(self) -> float:
        return self.capital + sum(self.positions.values())

    def position_sum(self) -> float:
        return sum(self.positions.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash": self.capital,
            "positions": dict(self.positions),
            "total_value": self.total_value(),
        }


class PortfolioManager:
    """
    多策略组合管理核心。
    - 接收多个策略实例（或 StrategyAdapter 包装的策略）
    - 根据 weight_mode 分配权重：equal | score | risk_parity
    - 使用 SignalAggregator 生成组合级信号
    - run_backtest / run_with_paper_trading 输出净值、持仓、交易记录
    """

    def __init__(
        self,
        strategies: List[Union[PortfolioStrategyBase, Any]],
        weight_mode: str = "equal",
        config: Optional[AggregatorConfig] = None,
    ):
        """
        :param strategies: 策略列表，可为 PortfolioStrategyBase 或具有 generate_signals 的策略
        :param weight_mode: equal | score | risk_parity
        :param config: 信号聚合配置
        """
        self._raw = strategies
        self.strategies: List[PortfolioStrategyBase] = []
        for s in strategies:
            if isinstance(s, PortfolioStrategyBase):
                self.strategies.append(s)
            else:
                self.strategies.append(StrategyAdapter(s))
        self.weight_mode = weight_mode.lower()
        self.aggregator = SignalAggregator(config)
        self.rebalancer = PortfolioRebalancer(freq="monthly")
        self._equity_curve: List[Dict[str, Any]] = []
        self._strategy_curves: Dict[str, List[Dict[str, Any]]] = {}
        self._trades: List[Dict[str, Any]] = []
        self._positions: Dict[str, Any] = {}

    def generate_portfolio_signal(self, market_data: pd.DataFrame) -> pd.Series:
        """
        生成组合级信号。
        :param market_data: K 线数据
        :return: 按日期索引的 Series，1=BUY, -1=SELL, 0=HOLD
        """
        if market_data is None or len(market_data) == 0:
            return pd.Series(dtype=float)
        signals = {s.name: s.generate_signal(market_data) for s in self.strategies}
        scores = {s.name: s.score(market_data) for s in self.strategies}
        weights = self._get_weights(market_data, scores)
        return self.aggregator.aggregate(signals, weights=weights, scores=scores)

    def _get_weights(
        self,
        data: pd.DataFrame,
        scores: Optional[Dict[str, float]] = None,
        volatilities: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        ids = [s.name for s in self.strategies]
        if self.weight_mode == "equal":
            w = WeightAllocator.equal_weight(self.strategies)
        elif self.weight_mode == "score" and scores:
            w = WeightAllocator.score_weight(self.strategies, scores)
        elif self.weight_mode == "risk_parity" and volatilities:
            w = WeightAllocator.risk_parity_weight(self.strategies, volatilities)
        else:
            w = WeightAllocator.equal_weight(self.strategies)
        return dict(zip(ids, w))

    def rebalance(self) -> None:
        """执行再平衡（权重模式下可在此更新权重）。"""
        self.rebalancer.mark_rebalanced("")

    def run_backtest(
        self,
        start_date: str,
        end_date: str,
        stock_code: str = "",
        timeframe: str = "D",
        run_plugin: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """
        运行组合回测。
        :param run_plugin: (strategy_id, symbol, start, end, tf) -> result；None 时使用 run_portfolio_backtest
        :return: { curve, holdCurve, summary, stats, trades, positions, performance_report }
        """
        from .portfolio import run_portfolio_backtest

        strat_ids = []
        for s in self.strategies:
            raw = getattr(s, "strategy", s)
            cls_name = raw.__class__.__name__ if hasattr(raw, "__class__") else ""
            if "MACross" in cls_name or "ma_cross" in str(raw).lower():
                strat_ids.append("ma_cross")
            elif "RSI" in cls_name or "rsi" in str(raw).lower():
                strat_ids.append("rsi")
            elif "MACD" in cls_name or "macd" in str(raw).lower():
                strat_ids.append("macd")
            elif "KDJ" in cls_name or "kdj" in str(raw).lower():
                strat_ids.append("kdj")
            elif "Breakout" in cls_name or "breakout" in str(raw).lower():
                strat_ids.append("breakout")
            else:
                try:
                    from strategies import PLUGIN_STRATEGIES
                    for sid, cls in PLUGIN_STRATEGIES.items():
                        if isinstance(raw, cls):
                            strat_ids.append(sid)
                            break
                    else:
                        strat_ids.append(s.name or "ma_cross")
                except Exception:
                    strat_ids.append(s.name or "ma_cross")
        weights = self._get_weights(pd.DataFrame(), None, None)
        w_list = [weights.get(s.name, 1.0 / len(self.strategies)) for s in self.strategies]
        strategies_json = [
            {"strategy_id": sid, "weight": w_list[i] if i < len(w_list) else 1.0 / len(strat_ids)}
            for i, sid in enumerate(strat_ids)
        ]
        if not stock_code and strategies_json:
            stock_code = "000001.XSHE"
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
        self._strategy_curves = result.get("strategy_curves", {})

        report = PerformanceReport.generate(
            result.get("curve"),
            result.get("strategy_curves"),
            {s.name: w_list[i] if i < len(w_list) else 1.0 / len(self.strategies) for i, s in enumerate(self.strategies)},
        )
        result["performance_report"] = report
        result["trades"] = result.get("signals", [])
        result["positions"] = {}
        return result

    def run_with_paper_trading(
        self,
        start_date: str,
        end_date: str,
        stock_code: str = "000001.XSHE",
        initial_cash: float = 1_000_000.0,
        load_kline_fn: Optional[Callable[[str, str, str], pd.DataFrame]] = None,
    ) -> Dict[str, Any]:
        """
        使用 paper_trading 执行组合。
        :return: { curve, summary, stats, trades, positions, performance_report }
        """
        try:
            from paper_trading import PaperBroker, TradeEngine, Performance
        except ImportError:
            return {"error": "paper_trading 模块未安装"}

        def _load(sym: str, start: str, end: str):
            try:
                from data.data_loader import load_kline as _lk
                df = _lk(sym, start, end, source="akshare")
                if df is None or len(df) < 20:
                    df = _lk(sym, start, end, source="database")
                return df
            except Exception:
                return pd.DataFrame()

        load_fn = load_kline_fn or _load
        sym = str(stock_code).split(".")[0] if "." in str(stock_code) else str(stock_code)
        order_book = sym + ".XSHG" if sym.startswith("6") else sym + ".XSHE"

        df = load_fn(sym, start_date, end_date)
        if df is None or len(df) < 20:
            return {"error": "无法加载 K 线数据"}

        portfolio_signal = self.generate_portfolio_signal(df)
        scores = {s.name: s.score(df) for s in self.strategies}
        weights = self._get_weights(df, scores)
        w_list = [weights.get(s.name, 1.0 / len(self.strategies)) for s in self.strategies]

        broker = PaperBroker(initial_cash=initial_cash)
        engine = TradeEngine(broker=broker)

        def _get_sigs(d):
            if d is None or len(d) == 0:
                return []
            last = d.iloc[-1]
            dt = str(last.get("date", d.index[-1] if d.index is not None else ""))[:10]
            close = float(last.get("close", 0))
            sig_list = []
            if dt in portfolio_signal.index:
                v = float(portfolio_signal.loc[dt])
                if v > 0:
                    sig_list.append({"date": dt, "type": "BUY", "price": close, "reason": "组合信号"})
                elif v < 0:
                    sig_list.append({"date": dt, "type": "SELL", "price": close, "reason": "组合信号"})
            return sig_list

        engine.run_from_kline(df, order_book, _get_sigs)

        eq = [(d, v) for d, v in broker.account.equity_curve]
        curve = [{"date": str(d)[:10], "value": v / initial_cash} for d, v in eq]
        self._equity_curve = curve
        self._trades = [
            {"date": r.date, "symbol": r.symbol, "side": r.side, "price": r.price, "amount": r.amount}
            for r in broker.account.trades
        ]
        self._positions = {k: {"amount": v.amount, "cost_price": v.cost_price} for k, v in broker.account.positions.items()}

        perf = Performance(broker.account).summary()
        report = PerformanceReport.generate(curve)
        return {
            "curve": curve,
            "holdCurve": curve,
            "summary": perf,
            "stats": perf,
            "trades": self._trades,
            "positions": self._positions,
            "performance_report": report,
        }
