"""
DuckDB 适配器：分析/回测/历史数据。委托 data_pipeline.storage.duckdb_manager。
"""
from __future__ import annotations

from typing import Any


def get_db_path() -> str:
    try:
        from data_pipeline.storage.duckdb_manager import get_db_path as _get
        return _get()
    except Exception:
        import os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "data", "quant_system.duckdb")


def get_conn(read_only: bool = False) -> Any:
    from data_pipeline.storage.duckdb_manager import get_conn as _get_conn
    return _get_conn(read_only=read_only)


def ensure_tables(conn: Any) -> None:
    from data_pipeline.storage.duckdb_manager import ensure_tables as _ensure
    _ensure(conn)


def get_analysis_store() -> Any:
    """返回分析存储对象：.get_conn(), .get_db_path(), .ensure_tables(conn)。"""
    class _Store:
        @staticmethod
        def get_conn(read_only: bool = False):
            return get_conn(read_only=read_only)

        @staticmethod
        def get_db_path():
            return get_db_path()

        @staticmethod
        def ensure_tables(conn):
            return ensure_tables(conn)

    return _Store()
