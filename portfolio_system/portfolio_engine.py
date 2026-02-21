# -*- coding: utf-8 -*-
"""
组合引擎：多策略 + 市场状态 + 风控，生成可执行交易信号。
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from .config import PortfolioConfig
from .market_regime import MarketRegime, MarketRegimeDetector
from .risk_control import RiskController, RiskLevel
from .strategy_pool import StrategyPool


class PortfolioEngine:
    """
    组合引擎：整合策略池、市场状态、风控，输出最终买卖信号。
    信号可接入 paper_trading 执行。
    """

    def __init__(self, config: Optional[PortfolioConfig] = None) -> None:
        self.config = config or PortfolioConfig()
        self.strategy_pool = StrategyPool(self.config.strategy_weights)
        self.regime_detector = MarketRegimeDetector()
        self.risk_controller = RiskController(
            stop_loss_pct=self.config.risk_config.stop_loss_pct,
            max_drawdown_warn=self.config.risk_config.max_drawdown_warn,
            max_drawdown_stop=self.config.risk_config.max_drawdown_stop,
        )
        self._load_index_fn: Optional[Callable[[str, str, str], pd.DataFrame]] = None

    def set_index_loader(self, fn: Callable[[str, str, str], pd.DataFrame]) -> None:
        """设置指数 K 线加载函数 (symbol, start, end) -> DataFrame。"""
        self._load_index_fn = fn

    def generate_signals(
        self,
        stock_df: pd.DataFrame,
        symbol: str,
        start_date: str,
        end_date: str,
        index_df: Optional[pd.DataFrame] = None,
        max_drawdown: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        生成组合级买卖信号。
        :param stock_df: 个股 K 线
        :param symbol: 标的代码
        :param start_date: 开始日期
        :param end_date: 结束日期
        :param index_df: 指数 K 线（用于市场状态），None 时自动加载
        :param max_drawdown: 当前最大回撤，用于风控
        """
        if stock_df is None or len(stock_df) < 20:
            return []
        if index_df is None and self._load_index_fn:
            index_df = self._load_index_fn(
                self.config.index_symbol, start_date, end_date
            )
        regime = self.regime_detector.detect(index_df) if index_df is not None else MarketRegime.NEUTRAL
        risk_level = self.risk_controller.get_risk_status(max_drawdown, index_df)
        position_scale = min(
            self.regime_detector.get_position_scale(regime),
            self.risk_controller.get_position_scale(risk_level),
        )
        if risk_level == RiskLevel.STOP or position_scale <= 0:
            return [{"date": str(stock_df.iloc[-1].get("date", ""))[:10], "type": "SELL", "price": float(stock_df["close"].iloc[-1]), "reason": "风控停止"}]
        strategy_signals = self.strategy_pool.run_all(stock_df)
        combined = self.strategy_pool.aggregate_signals(strategy_signals, "weighted")
        if position_scale < 1.0 and combined:
            for s in combined:
                s["position_scale"] = position_scale
        return combined
