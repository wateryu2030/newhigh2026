# -*- coding: utf-8 -*-
"""
策略插件基类。所有策略输出统一的 signals 格式。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd


class BaseStrategy(ABC):
    """多周期回测策略基类。输入 K 线 DataFrame，输出标准化买卖信号。"""

    name: str = "Base"
    description: str = ""

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        根据 K 线数据生成买卖信号。

        :param df: 至少包含 date(datetime index 或列), open, high, low, close, volume 的 DataFrame
        :return: 信号列表，每项为 {"date": str, "type": "BUY"|"SELL", "price": float, "reason": str}
                 日期统一 YYYY-MM-DD。
        """
        pass
