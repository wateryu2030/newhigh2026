"""
数据服务基类

所有数据服务继承此类，提供统一的连接管理和错误处理。
"""

from __future__ import annotations

from typing import Optional, List, Any
import duckdb
try:
    from ...lib.database import get_connection, ensure_core_tables
except (ImportError, ValueError):
    # Fallback: try direct import (for standalone testing)
    try:
        from lib.database import get_connection, ensure_core_tables
    except ImportError:
        get_connection = None
        ensure_core_tables = None


class BaseService:
    """数据服务基类"""

    def __init__(self, connection: Optional[duckdb.DuckDBPyConnection] = None):
        """
        初始化数据服务

        Args:
            connection: 可选的数据库连接，不提供则自动获取
        """
        self._connection = connection

    @property
    def connection(self) -> Optional[duckdb.DuckDBPyConnection]:
        """获取数据库连接"""
        if self._connection is None:
            if get_connection is not None:
                self._connection = get_connection(read_only=False)
                if self._connection and ensure_core_tables is not None:
                    ensure_core_tables(self._connection)
            else:
                #无法获取连接，返回 None
                pass
        return self._connection

    def close(self) -> None:
        """关闭连接"""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def execute(self, query: str, params: Optional[List] = None) -> Any:
        """
        执行 SQL 查询

        Args:
            query: SQL 查询语句
            params: 查询参数

        Returns:
            查询结果
        """
        conn = self.connection
        if not conn:
            return None

        try:
            if params:
                return conn.execute(query, params)
            return conn.execute(query)
        except (duckdb.Error, OSError, ValueError) as e:
            print(f"❌ SQL 执行失败：{e}")
            return None

    def fetchone(self, query: str, params: Optional[List] = None) -> Optional[tuple]:
        """执行查询并返回单行"""
        result = self.execute(query, params)
        if result:
            return result.fetchone()
        return None

    def fetchall(self, query: str, params: Optional[List] = None) -> List[tuple]:
        """执行查询并返回所有行"""
        result = self.execute(query, params)
        if result:
            return result.fetchall()
        return []

    def fetchdf(self, query: str, params: Optional[List] = None):
        """执行查询并返回 DataFrame"""
        result = self.execute(query, params)
        if result:
            return result.fetchdf()
        return None
