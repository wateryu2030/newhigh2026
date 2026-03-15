"""
存储抽象层：分析库（DuckDB）、交易库（PostgreSQL）、缓存（Redis）。
未配置 PostgreSQL 时交易存储回退 DuckDB（sim_* 表）。
"""

from __future__ import annotations

from .duckdb_adapter import get_analysis_store
from .redis_cache import get_cache

__all__ = ["get_analysis_store", "get_trade_store", "get_cache"]


def get_trade_store():
    """
    交易存储（订单、持仓）。优先 PostgreSQL；未配置时与分析共用 DuckDB。
    """
    from .postgres_adapter import get_trade_store as _pg

    store = _pg()
    if store is not None:
        return store
    return get_analysis_store()
