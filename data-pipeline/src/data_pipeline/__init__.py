# A股完整数据管道：采集 → ETL → DuckDB → API
from .storage.duckdb_manager import get_db_path, get_conn, ensure_tables
from .data_sources import get_source, list_sources

__all__ = [
    "get_db_path",
    "get_conn",
    "ensure_tables",
    "get_source",
    "list_sources",
    "run_incremental",
]


def run_incremental(source_id: str, force_full: bool = False, **kwargs) -> int:
    """
    执行指定数据源的增量更新。source_id 见 list_sources()。
    返回写入行数。
    """
    src = get_source(source_id)
    if not src:
        return 0
    conn = get_conn(read_only=False)
    ensure_tables(conn)
    try:
        n = src.run_incremental(conn, force_full=force_full, **kwargs)
        return n
    finally:
        conn.close()
