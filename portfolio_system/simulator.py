# -*- coding: utf-8 -*-
"""
模拟交易：组合信号接入 paper_trading 执行。
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from .config import PortfolioConfig
from .portfolio_engine import PortfolioEngine


class PortfolioSimulator:
    """
    组合模拟交易：将 PortfolioEngine 输出信号接入 paper_trading 执行。
    可对接 PaperBroker、TradeEngine。
    """

    def __init__(self, config: Optional[PortfolioConfig] = None) -> None:
        self.config = config or PortfolioConfig()
        self.engine = PortfolioEngine(config)
        self._load_stock_fn: Optional[Callable[[str, str, str], pd.DataFrame]] = None
        self._load_index_fn: Optional[Callable[[str, str, str], pd.DataFrame]] = None

    def set_data_loaders(
        self,
        load_stock: Optional[Callable[[str, str, str], pd.DataFrame]] = None,
        load_index: Optional[Callable[[str, str, str], pd.DataFrame]] = None,
    ) -> None:
        self._load_stock_fn = load_stock
        self._load_index_fn = load_index
        if load_index:
            self.engine.set_index_loader(load_index)

    def run(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        运行模拟交易。
        :return: { curve, trades, positions, summary }，对接 paper_trading 输出。
        """
        try:
            from paper_trading import PaperBroker, TradeEngine, Performance
        except ImportError:
            return {"error": "paper_trading 模块未安装"}
        if self._load_stock_fn is None:
            self._use_default_loaders()
        stock_df = self._load_stock_fn(symbol, start_date, end_date)
        if stock_df is None or len(stock_df) < 20:
            return {"error": "K 线数据不足", "curve": [], "trades": [], "positions": {}}
        index_df = None
        if self._load_index_fn:
            index_df = self._load_index_fn(
                self.config.index_symbol, start_date, end_date
            )
        order_book = symbol if "." in symbol else (symbol + ".XSHG" if symbol.startswith("6") else symbol + ".XSHE")
        broker = PaperBroker(initial_cash=self.config.initial_cash)
        engine = TradeEngine(broker=broker)
        max_dd = 0.0
        peak = 1.0

        def get_signals(df: pd.DataFrame) -> List[Dict[str, Any]]:
            nonlocal max_dd, peak
            if len(broker.account.equity_curve) > 0:
                vals = [v for _, v in broker.account.equity_curve]
                if vals:
                    nav = vals[-1] / self.config.initial_cash
                    if nav > peak:
                        peak = nav
                    if peak > 0:
                        dd = (peak - nav) / peak
                        if dd > max_dd:
                            max_dd = dd
            sub_idx = index_df.iloc[: len(df)] if index_df is not None and len(index_df) >= len(df) else None
            return self.engine.generate_signals(
                df, symbol, start_date, end_date,
                index_df=sub_idx,
                max_drawdown=max_dd,
            )

        engine.run_from_kline(stock_df, order_book, get_signals)
        eq = [(str(d)[:10], v) for d, v in broker.account.equity_curve]
        curve = [{"date": d, "value": v / self.config.initial_cash} for d, v in eq]
        trades = [
            {"date": r.date, "symbol": r.symbol, "side": r.side, "price": r.price, "amount": r.amount}
            for r in broker.account.trades
        ]
        positions = {
            k: {"amount": v.amount, "cost_price": v.cost_price}
            for k, v in broker.account.positions.items()
        }
        perf = Performance(broker.account).summary()
        return {
            "curve": curve,
            "trades": trades,
            "positions": positions,
            "summary": perf,
        }

    def _use_default_loaders(self) -> None:
        try:
            import os
            import sys
            _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            sys.path.insert(0, _root)
            from data.data_loader import load_kline
            def _load(sym: str, start: str, end: str) -> pd.DataFrame:
                return load_kline(sym, start, end, source="database")
            self._load_stock_fn = _load
            self._load_index_fn = lambda s, a, b: _load(s.split(".")[0], a, b)
            self.engine.set_index_loader(self._load_index_fn)
        except ImportError:
            def _empty(_: str, __: str, ___: str) -> pd.DataFrame:
                return pd.DataFrame()
            self._load_stock_fn = _empty
            self._load_index_fn = _empty
