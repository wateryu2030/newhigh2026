"""统一 DuckDB 连接，路径与 data_pipeline/data_engine 一致（data/quant_system.duckdb）。"""

from __future__ import annotations

import os

# 从 core/data_service 定位到 newhigh 根：data_service -> core -> src -> core -> newhigh
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_CORE_DIR = os.path.dirname(_THIS_DIR)  # core
_SRC_DIR = os.path.dirname(_CORE_DIR)  # src
_CORE_ROOT = os.path.dirname(_SRC_DIR)  # core (package root)
_NEWHIGH_ROOT = os.path.dirname(_CORE_ROOT)  # newhigh
DEFAULT_DB_PATH = os.path.join(_NEWHIGH_ROOT, "data", "quant_system.duckdb")


def get_db_path() -> str:
    """优先使用 core.config 统一配置，否则环境变量，最后默认路径。"""
    try:
        from core.config import get_db_path as _config_get_db_path

        return _config_get_db_path()
    except Exception:
        pass
    return (
        os.environ.get("QUANT_SYSTEM_DUCKDB_PATH", "").strip()
        or os.environ.get("NEWHIGH_DUCKDB_PATH", "").strip()
        or DEFAULT_DB_PATH
    )


def get_conn(read_only: bool = True):
    """获取 DuckDB 连接。Data Service 读多写少，默认只读。"""
    path = get_db_path()
    if not path or not os.path.isfile(path):
        return None
    try:
        import duckdb

        return duckdb.connect(path, read_only=read_only)
    except Exception:
        return None
