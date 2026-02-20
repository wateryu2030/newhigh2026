# -*- coding: utf-8 -*-
"""
A 股股票池数据接口模块。
统一从数据库、CSV、AKShare 加载股票列表与 K 线，供扫描器、组合、回测使用。
"""
from .stock_universe import (
    StockUniverse,
    load_universe_from_database,
    load_universe_from_csv,
    get_universe,
)
from .stock_pool import get_a_share_list, load_kline as load_kline_akshare
from .data_loader import load_kline as load_kline_unified

__all__ = [
    "StockUniverse",
    "load_universe_from_database",
    "load_universe_from_csv",
    "get_universe",
    "get_a_share_list",
    "load_kline_akshare",
    "load_kline_unified",
]
