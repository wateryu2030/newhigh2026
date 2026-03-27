"""
统一数据库入口（薄代理）

**单一事实源**：`data_pipeline.storage.duckdb_manager`
- `get_db_path` / `get_conn`：路径优先级、`.env`、建目录
- `ensure_tables`：全库 DDL（管道 / Gateway / 模拟盘 / Hongshan 等）

本模块保留 `get_connection`、`ensure_core_tables`、`get_table_counts` 等历史 API，
内部全部委托给 duckdb_manager，避免 lib 与管道各维护一套逻辑。

使用示例:
    from lib.database import get_connection, ensure_core_tables

    conn = get_connection()
    if conn:
        ensure_core_tables(conn)
        conn.close()

Author: OpenClaw Agent
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import duckdb

DBPath = Union[str, Path]
DuckDBConnection = duckdb.DuckDBPyConnection

_LIB_DIR: Path = Path(__file__).resolve().parent
_PROJECT_ROOT: Path = _LIB_DIR.parent
DEFAULT_DB_PATH: Path = _PROJECT_ROOT / "data" / "quant_system.duckdb"


def _ensure_data_pipeline_on_path() -> None:
    """使 `import data_pipeline` 可用（标准仓库布局：data-pipeline/src）。"""
    dp_src = _PROJECT_ROOT / "data-pipeline" / "src"
    if dp_src.is_dir():
        s = str(dp_src.resolve())
        if s not in sys.path:
            sys.path.insert(0, s)


def get_db_path() -> str:
    """
    返回统一 DuckDB 文件路径（委托 duckdb_manager）。

    优先级：QUANT_DB_PATH → QUANT_SYSTEM_DUCKDB_PATH → NEWHIGH_MARKET_DUCKDB_PATH
    → NEWHIGH_DB_PATH；未设置时再读仓库根 `.env`；默认 `<repo>/data/quant_system.duckdb`。
    """
    _ensure_data_pipeline_on_path()
    from data_pipeline.storage.duckdb_manager import get_db_path as _get_db_path

    return _get_db_path()


def get_connection(read_only: bool = False) -> Optional[DuckDBConnection]:
    """
    获取数据库连接（委托 `duckdb_manager.get_conn`）。

    与 Gateway / 审计中间件共用同一库时，请使用默认 ``read_only=False``，
    避免同进程混用只读与读写连接导致 DuckDB 报错。
    """
    try:
        _ensure_data_pipeline_on_path()
        from data_pipeline.storage.duckdb_manager import get_conn

        return get_conn(read_only=read_only)
    except Exception as e:
        print(f"❌ 数据库连接失败：{e}")
        return None


def ensure_core_tables(conn: DuckDBConnection) -> None:
    """
    确保业务所需全部表存在（委托 ``duckdb_manager.ensure_tables``）。

    名称保留为 ``ensure_core_tables`` 以兼容历史调用；DDL 不再在此处重复维护。
    """
    _ensure_data_pipeline_on_path()
    from data_pipeline.storage.duckdb_manager import ensure_tables

    ensure_tables(conn)


def get_table_counts(conn: DuckDBConnection) -> Dict[str, int]:
    """
    返回当前库中已有表的行数（``SHOW TABLES``，与 ensure_tables 创建的集合一致）。
    """
    counts: Dict[str, int] = {}
    try:
        rows: List[Any] = conn.execute("SHOW TABLES").fetchall()
        names = [str(r[0]) for r in rows or []]
    except Exception:
        names = []
    for name in names:
        try:
            result = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()
            counts[name] = int(result[0]) if result else 0
        except Exception:
            counts[name] = 0
    return counts
