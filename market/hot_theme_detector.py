# -*- coding: utf-8 -*-
"""
热点识别引擎：板块涨幅 + 资金流入 + 换手/成交额 → 热点强度评分。
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
import pandas as pd

from .sector_strength import get_sector_strength
from .money_flow import get_stock_money_flow, get_sector_fund_flow_rank


class HotThemeDetector:
    """
    热点强度 = 板块涨幅权重 + 资金流入权重 + 换手/成交额爆发权重。
    输出 0~100 热点强度评分。
    """

    def __init__(
        self,
        sector_weight: float = 0.4,
        money_flow_weight: float = 0.4,
        turnover_weight: float = 0.2,
    ):
        self.sector_weight = sector_weight
        self.money_flow_weight = money_flow_weight
        self.turnover_weight = turnover_weight

    def sector_score(self, sector_name: Optional[str] = None) -> float:
        """板块维度强度 0~100。若指定 sector_name 则取该板块涨幅映射分。"""
        rows = get_sector_strength(top_n=50)
        if not rows:
            return 50
        if sector_name:
            for r in rows:
                if r.get("name") == sector_name:
                    return float(r.get("strength", 50))
            return 50
        # 全市场：取前 5 板块平均强度
        top = rows[:5]
        return sum(r.get("strength", 50) for r in top) / len(top) if top else 50

    def money_flow_score(self, symbol: str) -> float:
        """个股资金流评分 0~100。"""
        d = get_stock_money_flow(symbol, days=5)
        return float(d.get("score", 50))

    def hot_strength_for_stock(
        self,
        symbol: str,
        sector_name: Optional[str] = None,
        turnover_ratio: Optional[float] = None,
        turnover_ma_ratio: Optional[float] = None,
    ) -> float:
        """
        单只股票的热点强度。
        turnover_ratio: 当前换手率；turnover_ma_ratio: 当前换手/均量换手，>1 为放量。
        """
        s = self.sector_score(sector_name) * self.sector_weight
        m = self.money_flow_score(symbol) * self.money_flow_weight
        t = 50
        if turnover_ratio is not None and turnover_ma_ratio is not None and turnover_ma_ratio > 0:
            t = min(100, 50 + (turnover_ma_ratio - 1) * 25)  # 放量加分
        t *= self.turnover_weight
        return round(s + m + t, 2)


def get_hot_strength(
    symbol: str,
    sector_name: Optional[str] = None,
) -> float:
    """
    便捷函数：获取单只股票的热点强度 0~100。
    """
    d = HotThemeDetector()
    return d.hot_strength_for_stock(symbol, sector_name=sector_name)
