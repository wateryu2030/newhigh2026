#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite → DuckDB 一键迁移：把 astock.db 里的表直接复制到 quant.duckdb。

- 只做本地拷贝，不访问网络，通常几十秒内完成（百万级日线）。
- 若你已有完整 SQLite 日线数据，用本脚本复制到 DuckDB 即可，无需再从 AKShare 全量拉取。
- 不修改 astock.db，只生成/覆盖 data/quant.duckdb。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def main() -> int:
    sqlite_path = os.path.join(_ROOT, "data", "astock.db")
    duckdb_path = os.path.join(_ROOT, "data", "quant.duckdb")

    if not os.path.exists(sqlite_path):
        print(f"未找到 SQLite 数据库: {sqlite_path}")
        return 1

    try:
        import duckdb
    except ImportError:
        print("请安装 duckdb: pip install duckdb")
        return 1

    os.makedirs(os.path.dirname(duckdb_path), exist_ok=True)
    if os.path.exists(duckdb_path):
        os.remove(duckdb_path)

    conn = duckdb.connect(duckdb_path)
    conn.execute("INSTALL sqlite")
    conn.execute("LOAD sqlite")
    sqlite_abs = os.path.abspath(sqlite_path)
    conn.execute(f"ATTACH '{sqlite_abs}' AS sqlite_db (TYPE sqlite)")

    # 迁移表
    tables = ["stocks", "daily_bars", "trading_calendar"]
    for table in tables:
        try:
            conn.execute(f"""
                CREATE TABLE {table} AS
                SELECT * FROM sqlite_db.{table}
            """)
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n} 行")
        except Exception as e:
            print(f"  {table}: 跳过 ({e})")

    # 创建主键/索引（DuckDB 无 PRIMARY KEY 约束则仅建索引）
    try:
        conn.execute("CREATE INDEX idx_daily_order ON daily_bars(order_book_id)")
        conn.execute("CREATE INDEX idx_daily_date ON daily_bars(trade_date)")
    except Exception:
        pass

    conn.close()
    print(f"✅ 迁移完成: {duckdb_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
