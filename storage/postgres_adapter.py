"""
PostgreSQL 适配器（占位）：交易库订单/持仓。当前未启用，交易数据仍用 DuckDB。
"""

from __future__ import annotations

from typing import Any, List, Optional


def get_trade_conn() -> Optional[Any]:
    """返回 PostgreSQL 连接；未配置 DATABASE_URL 时返回 None。"""
    import os

    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        return None
    try:
        import psycopg2

        return psycopg2.connect(url)
    except Exception:
        return None


def ensure_trade_tables(conn: Any) -> None:
    """创建 orders、trades、positions、portfolio_equity 表（若不存在）。"""
    # 占位：实际 SQL 按业务定义
    pass


def get_trade_store() -> Any:
    """返回交易存储对象；当前返回 None 表示使用 DuckDB 模拟表。"""
    if get_trade_conn() is None:
        return None
    return _PostgresTradeStore()


class _PostgresTradeStore:
    def get_conn(self) -> Optional[Any]:
        return get_trade_conn()

    def ensure_tables(self, conn: Any) -> None:
        ensure_trade_tables(conn)
