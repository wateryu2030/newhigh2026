"""
数据服务层

提供统一的数据访问接口，所有模块通过此层访问数据库。

架构:
    lib/           ← 基础设施 (数据库连接)
    core/          ← 核心服务 (配置/数据类型)
    data/          ← 数据服务层 (本模块)
    scanner/       ← 扫描器
    ai/            ← AI 模型
    strategy/      ← 策略引擎
"""

from .base import BaseService
from .stock_service import StockService
from .news_service import NewsService
from .signal_service import SignalService
from .emotion_service import EmotionService
from .db import get_conn, get_db_path, get_astock_duckdb_available

__all__ = [
    "BaseService",
    "StockService",
    "NewsService",
    "SignalService",
    "EmotionService",
    "get_conn",
    "get_db_path",
    "get_astock_duckdb_available",
]
