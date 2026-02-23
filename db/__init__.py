# -*- coding: utf-8 -*-
"""
DuckDB 数据层：连接管理、Parquet、性能优化。
"""
from .duckdb_manager import DuckDBManager
from .performance import apply_duckdb_performance

__all__ = ["DuckDBManager", "apply_duckdb_performance"]
