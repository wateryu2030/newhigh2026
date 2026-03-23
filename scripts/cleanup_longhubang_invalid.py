#!/usr/bin/env python3
"""
删除 a_stock_longhubang 中 lhb_date 为 NULL 的历史脏行（会导致下钻同代码刷屏、日期 NaT）。
用法（项目根）:
  PYTHONPATH=... python scripts/cleanup_longhubang_invalid.py
或先 source .venv 后:
  python scripts/cleanup_longhubang_invalid.py
"""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
if os.path.join(_ROOT, "data-pipeline", "src") not in sys.path:
    sys.path.insert(0, os.path.join(_ROOT, "data-pipeline", "src"))


def main() -> None:
    from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

    path = get_db_path()
    if not path or not os.path.isfile(path):
        print("未找到 DuckDB:", path)
        sys.exit(1)
    conn = get_conn(read_only=False)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM a_stock_longhubang WHERE lhb_date IS NULL"
        ).fetchone()[0]
        conn.execute("DELETE FROM a_stock_longhubang WHERE lhb_date IS NULL")
        print(f"已删除 lhb_date 为空的行数: {int(n)}，库: {path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
