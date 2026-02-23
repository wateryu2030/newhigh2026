# -*- coding: utf-8 -*-
"""
DuckDB 模块测试：写入行情、查询速度、DataFrame 读写。
"""
import os
import sys
import time

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def test_duckdb_manager():
    """测试 DuckDBManager 写入与查询。"""
    try:
        from db import DuckDBManager
    except ImportError:
        print("SKIP: duckdb 未安装")
        return
    db_path = os.path.join(_ROOT, "data", "test_quant.duckdb")
    if os.path.exists(db_path):
        os.remove(db_path)
    db = DuckDBManager(db_path)
    # 写入行情
    df = pd.DataFrame({
        "order_book_id": ["000001.XSHE"] * 100,
        "trade_date": pd.date_range("2024-01-01", periods=100, freq="B").strftime("%Y-%m-%d"),
        "open": 10.0,
        "high": 11.0,
        "low": 9.5,
        "close": 10.5,
        "volume": 1e6,
        "total_turnover": 1e7,
        "adjust_factor": 1.0,
    })
    db.insert_df("daily_bars", df)
    # 查询
    t0 = time.perf_counter()
    out = db.query_df("SELECT * FROM daily_bars WHERE order_book_id = '000001.XSHE' AND trade_date >= '2024-03-01'")
    elapsed = time.perf_counter() - t0
    assert len(out) >= 1, "应有数据"
    print(f"  查询 {len(out)} 行 耗时 {elapsed*1000:.1f} ms")
    db.close()
    if os.path.exists(db_path):
        os.remove(db_path)
    print("  DuckDBManager OK")


def test_migration():
    """测试迁移脚本（仅当存在 astock.db 时）。"""
    sqlite_path = os.path.join(_ROOT, "data", "astock.db")
    if not os.path.exists(sqlite_path):
        print("  SKIP: 无 astock.db，未执行迁移测试")
        return
    try:
        import duckdb
    except ImportError:
        print("  SKIP: duckdb 未安装")
        return
    duck_path = os.path.join(_ROOT, "data", "quant_migrate_test.duckdb")
    if os.path.exists(duck_path):
        os.remove(duck_path)
    conn = duckdb.connect(duck_path)
    conn.execute("INSTALL sqlite")
    conn.execute("LOAD sqlite")
    conn.execute(f"ATTACH '{os.path.abspath(sqlite_path)}' AS sqlite_db (TYPE sqlite)")
    conn.execute("CREATE TABLE daily_bars AS SELECT * FROM sqlite_db.daily_bars")
    n = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
    conn.close()
    if os.path.exists(duck_path):
        os.remove(duck_path)
    print(f"  迁移测试 OK (daily_bars 行数: {n})")


if __name__ == "__main__":
    print("DuckDB 与数据层测试")
    test_duckdb_manager()
    test_migration()
    print("Done")
