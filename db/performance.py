# -*- coding: utf-8 -*-
"""
DuckDB 性能优化：线程数、内存限制、对象缓存。
Mac 本地友好，自动检测 CPU 核心数。
"""
from __future__ import annotations
import os
from typing import Optional


def get_default_threads() -> int:
    """自动检测 CPU 核心数，留 1 给系统，最少 1 最多 8。"""
    try:
        n = os.cpu_count() or 4
        return max(1, min(8, n - 1))
    except Exception:
        return 4


def get_default_memory_limit() -> str:
    """默认内存限制，Mac 友好。"""
    return os.environ.get("DUCKDB_MEMORY_LIMIT", "4GB")


def apply_duckdb_performance(
    conn,
    threads: Optional[int] = None,
    memory_limit: Optional[str] = None,
) -> None:
    """
    对已打开的 DuckDB 连接应用性能 PRAGMA。
    """
    threads = threads if threads is not None else get_default_threads()
    memory_limit = memory_limit or get_default_memory_limit()
    conn.execute(f"PRAGMA threads={threads}")
    conn.execute(f"PRAGMA memory_limit='{memory_limit}'")
    try:
        conn.execute("PRAGMA enable_object_cache=true")
    except Exception:
        pass
