#!/usr/bin/env python3
"""
把 astock 的 DuckDB 数据复制到 newhigh 本地，两套目录完全独立。
复制后 newhigh 只读本仓库 data/quant_system.duckdb，不再依赖 astock 目录。

用法（在 newhigh 仓库根目录）:
  python scripts/copy_astock_duckdb_to_newhigh.py
  python scripts/copy_astock_duckdb_to_newhigh.py --source /path/to/astock/data/quant_system.duckdb --dest ./data/quant_system.duckdb
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SOURCE = "/Users/apple/astock/data/quant_system.duckdb"
DEFAULT_DEST = os.path.join(ROOT, "data", "quant_system.duckdb")


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy astock DuckDB to newhigh/data/quant_system.duckdb")
    parser.add_argument(
        "--source",
        default=os.environ.get("ASTOCK_DUCKDB_PATH", DEFAULT_SOURCE),
        help="Source DuckDB (astock)",
    )
    parser.add_argument(
        "--dest",
        default=os.environ.get(
            "QUANT_SYSTEM_DUCKDB_PATH", os.environ.get("NEWHIGH_DUCKDB_PATH", DEFAULT_DEST)
        ),
        help="Destination DuckDB (newhigh, default quant_system.duckdb)",
    )
    parser.add_argument("--skip-news", action="store_true", help="Skip copying news_items")
    args = parser.parse_args()

    source = os.path.abspath(args.source)
    dest = os.path.abspath(args.dest)

    if not os.path.isfile(source):
        print(f"Source not found: {source}", file=sys.stderr)
        return 1

    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)

    try:
        import duckdb
    except ImportError:
        print("Need duckdb: pip install duckdb", file=sys.stderr)
        return 1

    # 连接目标库（新建或覆盖），并 attach 源库为只读
    conn = duckdb.connect(dest)
    src_escaped = source.replace("'", "''")
    conn.execute(f"ATTACH '{src_escaped}' AS src (READ_ONLY)")

    # 表结构需与 astock 一致（daily_bars, stocks, news_items）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_bars (
            order_book_id VARCHAR NOT NULL,
            trade_date DATE NOT NULL,
            adjust_type VARCHAR NOT NULL DEFAULT 'qfq',
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            total_turnover DOUBLE,
            adjust_factor DOUBLE DEFAULT 1.0,
            PRIMARY KEY (order_book_id, trade_date, adjust_type)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            order_book_id VARCHAR PRIMARY KEY,
            symbol VARCHAR NOT NULL,
            name VARCHAR,
            market VARCHAR,
            listed_date VARCHAR,
            de_listed_date VARCHAR,
            type VARCHAR,
            updated_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_items (
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            symbol VARCHAR,
            source_site VARCHAR,
            source VARCHAR,
            title VARCHAR,
            content VARCHAR,
            url VARCHAR,
            keyword VARCHAR,
            tag VARCHAR,
            publish_time VARCHAR,
            sentiment_score DOUBLE,
            sentiment_label VARCHAR
        )
    """)

    # 复制数据：先清空再插入（保证幂等）
    for table in ["daily_bars", "stocks"]:
        try:
            conn.execute(f"DELETE FROM {table}")
            conn.execute(f"INSERT INTO {table} SELECT * FROM src.{table}")
            n = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {n} rows")
        except Exception as e:
            print(f"  {table}: skip ({e})")

    if not args.skip_news:
        try:
            conn.execute("DELETE FROM news_items")
            conn.execute("INSERT INTO news_items SELECT * FROM src.news_items")
            n = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
            print(f"  news_items: {n} rows")
        except Exception as e:
            print(f"  news_items: skip ({e})")

    try:
        conn.execute("DETACH src")
    except Exception:
        pass
    conn.close()
    print(f"Done. Newhigh DB: {dest}")
    if not args.skip_news:
        print("提示：若源库 news_items 有重复，可执行去重: python scripts/dedup_news_items.py --dry-run 查看后，再执行 python scripts/dedup_news_items.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
