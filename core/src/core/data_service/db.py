"""
数据库连接管理

为 core.data_service 层提供统一接口。**路径、连接、建表** 的唯一实现见
``data_pipeline.storage.duckdb_manager``；``lib.database`` 与为本模块的代理链，
避免两套 DDL / 两套路径逻辑。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
import duckdb

# 代理到 lib.database
try:
    from lib.database import (
        get_connection as _get_connection,
        get_db_path as _get_db_path,
    )
except ImportError:
    _get_connection = None
    _get_db_path = None


def get_db_path() -> str:
    """
    获取数据库路径

    Returns:
        数据库文件绝对路径
    """
    if _get_db_path:
        return _get_db_path()

    # Fallback: 默认路径
    lib_dir = Path(__file__).resolve().parent.parent.parent
    project_root = lib_dir.parent
    return str(project_root / "data" / "quant_system.duckdb")


def get_conn(read_only: bool = False) -> Optional[duckdb.DuckDBPyConnection]:
    """
    获取数据库连接

    Args:
        read_only: 默认 False；与同进程内 duckdb_manager / 审计写入共用库时勿用 True，
            否则会触发 DuckDB「different configuration」错误。

    Returns:
        DuckDB 连接对象，失败返回 None
    """
    if _get_connection:
        return _get_connection(read_only=read_only)

    # Fallback: 直接连接
    try:
        db_path = get_db_path()
        if not os.path.isfile(db_path):
            return None
        return duckdb.connect(db_path, read_only=read_only)
    except (OSError, duckdb.Error):
        return None


def get_astock_duckdb_available() -> bool:
    """
    检查 A 股 DuckDB 是否可用

    Returns:
        True if 数据库文件存在且可连接，否则 False
    """
    try:
        conn = get_conn(read_only=False)
        if conn is None:
            return False
        # 简单测试查询
        conn.execute("SELECT 1")
        conn.close()
        return True
    except (OSError, duckdb.Error):
        return False


__all__ = [
    "get_conn",
    "get_db_path",
    "get_astock_duckdb_available",
]
