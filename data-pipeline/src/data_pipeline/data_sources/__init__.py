"""
数据源抽象与插件：多数据源统一接口，支持增量更新。
"""

from .base import BaseDataSource, register_source, get_source, list_sources

__all__ = [
    "BaseDataSource",
    "register_source",
    "get_source",
    "list_sources",
]

# 注册内置 A 股数据源
from . import ashare_daily_kline  # noqa: F401
from . import ashare_longhubang  # noqa: F401

# 扩展数据源：Tushare（需 TUSHARE_TOKEN）、Binance（公开 API）
from . import tushare_source  # noqa: F401
from . import binance_source  # noqa: F401
