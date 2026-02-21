# -*- coding: utf-8 -*-
"""
策略接口抽象层：供组合管理使用的统一接口。
将 strategies.BaseStrategy 的 generate_signals 转为 generate_signal (Series) 与 score。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np


class PortfolioStrategyBase(ABC):
    """供组合管理使用的策略基类。"""

    name: str = "Base"

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame) -> pd.Series:
        """
        生成日度信号序列。
        :param data: K 线数据，含 date / datetime index, open, high, low, close, volume
        :return: 按日期索引的 Series，值 1=BUY, -1=SELL, 0=HOLD
        """
        pass

    @abstractmethod
    def score(self, data: pd.DataFrame) -> float:
        """
        策略当前评分（用于权重分配或信号过滤）。
        :param data: K 线数据
        :return: 0~1 或任意实数，越高越好
        """
        pass


class StrategyAdapter(PortfolioStrategyBase):
    """
    将 strategies.BaseStrategy (generate_signals -> List[Dict]) 适配为 PortfolioStrategyBase。
    """

    def __init__(self, strategy: Any, score_fn: Optional[Any] = None):
        """
        :param strategy: 具有 generate_signals(df) -> List[Dict] 的策略实例
        :param score_fn: 可选 (strategy, df) -> float；默认用最近收益简单估计
        """
        self.strategy = strategy
        self.score_fn = score_fn
        self.name = getattr(strategy, "name", "Unknown")

    def generate_signal(self, data: pd.DataFrame) -> pd.Series:
        if data is None or len(data) == 0:
            return pd.Series(dtype=float)
        signals = self.strategy.generate_signals(data)
        dates = self._get_dates(data)
        out = pd.Series(0.0, index=dates)
        for s in signals:
            d = str(s.get("date", ""))[:10]
            typ = str(s.get("type", "HOLD")).upper()
            if typ == "BUY":
                out[d] = 1.0
            elif typ == "SELL":
                out[d] = -1.0
        return out

    def score(self, data: pd.DataFrame) -> float:
        if self.score_fn is not None:
            return float(self.score_fn(self.strategy, data))
        return self._default_score(data)

    def _get_dates(self, df: pd.DataFrame) -> pd.Index:
        if "date" in df.columns:
            return pd.Index(sorted(df["date"].astype(str).str[:10].unique()))
        if df.index is not None and len(df.index) > 0:
            return pd.Index(sorted(str(d)[:10] for d in df.index.unique()))
        return pd.Index([])

    def _default_score(self, data: pd.DataFrame) -> float:
        """默认评分：基于最近 20 日收益率的简单估计。"""
        if data is None or len(data) < 20:
            return 0.5
        try:
            close = data["close"].astype(float)
            ret = (close.iloc[-1] - close.iloc[-20]) / (close.iloc[-20] or 1e-6)
            return min(1.0, max(0.0, 0.5 + ret * 2))
        except Exception:
            return 0.5
