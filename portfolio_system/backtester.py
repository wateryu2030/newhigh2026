# -*- coding: utf-8 -*-
"""
回测引擎：运行组合回测，输出净值曲线、交易记录、统计指标。
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from .config import PortfolioConfig
from .portfolio_engine import PortfolioEngine
from .performance import PerformanceReport


class Backtester:
    """
    组合回测引擎。
    目标年化 20~40%，输出净值曲线、交易记录、绩效报告。
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
        """设置 K 线加载函数。"""
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
        运行回测。
        :return: { curve, signals, summary, stats, performance_report }
        """
        if self._load_stock_fn is None:
            self._use_default_loaders()
        stock_df = self._load_stock_fn(symbol, start_date, end_date)
        if stock_df is None or len(stock_df) < 20:
            return {"error": "K 线数据不足", "curve": [], "signals": [], "summary": {}}
        index_df = None
        if self._load_index_fn:
            index_df = self._load_index_fn(
                self.config.index_symbol, start_date, end_date
            )
        if "date" not in stock_df.columns and stock_df.index is not None:
            stock_df = stock_df.copy()
            stock_df["date"] = stock_df.index.astype(str).str[:10]
        dates = sorted(stock_df["date"].drop_duplicates().tolist())
        if not dates:
            return {"error": "无有效日期", "curve": [], "signals": [], "summary": {}}
        signals: List[Dict[str, Any]] = []
        nav = 1.0
        curve: List[Dict[str, Any]] = [{"date": str(dates[0])[:10], "value": nav}]
        peak = 1.0
        max_dd = 0.0
        position = 0
        prev_close = float(stock_df[stock_df["date"] == dates[0]]["close"].iloc[0])
        for i, d in enumerate(dates):
            sub = stock_df[stock_df["date"] == d]
            if sub.empty:
                continue
            close = float(sub["close"].iloc[-1])
            sub_df = stock_df[stock_df["date"] <= d].copy()
            idx_sub = None
            if index_df is not None and len(index_df) > 0:
                n = min(len(index_df), len(sub_df))
                idx_sub = index_df.iloc[:n]
            sigs = self.engine.generate_signals(
                sub_df, symbol, start_date, end_date,
                index_df=idx_sub,
                max_drawdown=max_dd,
            )
            d_str = str(d)[:10]
            day_sigs = [s for s in sigs if str(s.get("date", ""))[:10] == d_str]
            for s in day_sigs:
                t = str(s.get("type", "")).upper()
                price = float(s.get("price", close))
                signals.append({"date": d_str, "type": t, "price": price, "reason": s.get("reason", "")})
                if t == "BUY":
                    position = 1
                elif t == "SELL":
                    position = 0
            if i > 0 and position == 1 and prev_close > 0:
                nav *= close / prev_close
            if nav > peak:
                peak = nav
            if peak > 0:
                dd = (peak - nav) / peak
                if dd > max_dd:
                    max_dd = dd
            curve.append({"date": d_str, "value": round(nav, 6)})
            prev_close = close
        total_return = nav - 1.0
        perf = PerformanceReport.generate(curve)
        return {
            "curve": curve,
            "signals": signals,
            "summary": {
                "total_return": total_return,
                "return_rate": total_return,
                "max_drawdown": max_dd,
                "sharpe_ratio": perf.get("sharpe_ratio", 0),
            },
            "stats": {
                "trade_count": len([s for s in signals if s.get("type") in ("BUY", "SELL")]),
                "final_nav": nav,
            },
            "performance_report": perf,
        }

    def _use_default_loaders(self) -> None:
        """使用默认数据加载。"""
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
