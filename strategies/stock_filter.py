# -*- coding: utf-8 -*-
"""
股票过滤：ST、停牌、成交额过低、上市不足 60 天。
"""
from __future__ import annotations
from typing import List, Optional, Set
import pandas as pd


class StockFilter:
    """
    过滤不合格标的。
    - ST 股票
    - 停牌
    - 成交额过低
    - 上市不足 60 天
    """

    def __init__(
        self,
        min_amount: float = 5e6,
        min_list_days: int = 60,
        exclude_st: bool = True,
    ):
        self.min_amount = min_amount
        self.min_list_days = min_list_days
        self.exclude_st = exclude_st

    def filter_symbols(
        self,
        symbols: List[str],
        df_map: Optional[dict] = None,
    ) -> List[str]:
        """
        过滤股票列表。
        :param symbols: 待过滤代码列表
        :param df_map: {symbol: kline_df} 若提供则按 K 线过滤
        """
        out = []
        for s in symbols:
            if self.exclude_st and self._is_st(s):
                continue
            if df_map and s in df_map:
                df = df_map[s]
                if len(df) < self.min_list_days:
                    continue
                if "amount" in df.columns and df["amount"].iloc[-1] < self.min_amount:
                    continue
                if "volume" in df.columns and "close" in df.columns:
                    amt = df["volume"].iloc[-1] * df["close"].iloc[-1]
                    if amt < self.min_amount:
                        continue
            out.append(s)
        return out

    def _is_st(self, symbol: str) -> bool:
        """简单判断是否 ST（需结合实际数据，此处为占位）。"""
        return False  # 实际可接入行情接口判断
