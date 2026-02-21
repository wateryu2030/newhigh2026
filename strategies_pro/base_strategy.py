# -*- coding: utf-8 -*-
"""
机构级策略抽象基类：统一接口，与现有组合管理兼容。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import pandas as pd


# 支持单标的 DataFrame 或多标的 Dict[symbol, DataFrame]
MarketDataType = Union[pd.DataFrame, Dict[str, pd.DataFrame]]


class BaseStrategy(ABC):
    """机构级策略抽象接口。"""

    name: str = "Base"

    @abstractmethod
    def generate_signals(self, market_data: MarketDataType) -> pd.DataFrame:
        """
        返回交易信号。
        :return: DataFrame 至少含列 symbol, signal, weight, stop_loss（可选）
        """
        pass

    @abstractmethod
    def select_stocks(self, market_data: MarketDataType) -> List[str]:
        """选股，返回标的代码列表。"""
        pass

    def position_size(self, capital: float) -> Dict[str, float]:
        """
        仓位分配。默认等权；子类可覆盖。
        :return: { symbol: 分配资金比例 0~1 }
        """
        return {}

    def score(self) -> float:
        """
        策略评分 0~1，用于动态权重。
        子类可覆盖，默认 0.5。
        """
        return 0.5

    def _ensure_df(self, market_data: MarketDataType, symbol: Optional[str] = None) -> pd.DataFrame:
        """将 market_data 转为单标的 DataFrame。"""
        if isinstance(market_data, pd.DataFrame):
            return market_data
        if isinstance(market_data, dict) and symbol and symbol in market_data:
            return market_data[symbol]
        if isinstance(market_data, dict) and len(market_data) > 0:
            return next(iter(market_data.values()))
        return pd.DataFrame()

    def _panel_to_dict(self, market_data: pd.DataFrame, symbol_col: str = "symbol") -> Dict[str, pd.DataFrame]:
        """若 market_data 为多标的面板数据，按 symbol 拆成 dict。"""
        if market_data is None or len(market_data) == 0 or symbol_col not in market_data.columns:
            return {}
        return {s: market_data[market_data[symbol_col] == s].copy() for s in market_data[symbol_col].unique()}
