"""
共享库模块 - 所有模块共用的基础设施

提供：
- 数据库连接管理
- 配置加载
- 工具函数
- 常量定义
"""

from .database import get_connection, get_db_path, ensure_core_tables
from .utils import parse_symbol, is_ashare_symbol, format_number
from .constants import DEFAULT_DB_PATH, PROJECT_ROOT

__all__ = [
    # 数据库
    "get_connection",
    "get_db_path",
    "ensure_core_tables",
    # 工具
    "parse_symbol",
    "is_ashare_symbol",
    "format_number",
    # 常量
    "DEFAULT_DB_PATH",
    "PROJECT_ROOT",
]
