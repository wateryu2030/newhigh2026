#!/usr/bin/env python3
"""
删除 news_items 表中重复记录，保留 (title, publish_time) 唯一，保留 ts 最新的一条。
使用与 Gateway 相同的 quant_system.duckdb（core.data_service.db.get_db_path()）。

采集逻辑现状：
- data_pipeline/collectors/caixin_news.py：按 url 存在则跳过，不插重复。
- news_collector_optimized.py：按 (title, publish_time) NOT EXISTS 再插入。
- scripts/copy_astock_duckdb_to_newhigh.py：整表复制，源库若有重复会带入。
建议：从 astock 复制或大批量导入后执行本脚本一次；也可定期执行（如每周）。

用法：在项目根目录执行
  . .venv/bin/activate && python scripts/dedup_news_items.py
  python scripts/dedup_news_items.py --dry-run   # 仅打印将删除的数量，不写库
"""
from __future__ import annotations

import argparse
import os
import sys

# 项目根
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def get_conn(read_only: bool = False):
    """使用与 Gateway 一致的 DB 路径。"""
    from core.data_service.db import get_db_path
    import duckdb
    path = get_db_path()
    if not path or not os.path.isfile(path):
        return None
    return duckdb.connect(path, read_only=read_only)


def main() -> int:
    ap = argparse.ArgumentParser(description="news_items 表按 (title, publish_time) 去重")
    ap.add_argument("--dry-run", action="store_true", help="仅统计，不删除")
    args = ap.parse_args()

    conn = get_conn(read_only=args.dry_run)
    if conn is None:
        print("未找到 quant_system.duckdb，请确认路径（QUANT_SYSTEM_DUCKDB_PATH 或 data/quant_system.duckdb）")
        return 1

    try:
        total = conn.execute("SELECT COUNT(*) FROM news_items").fetchone()[0]
        if total == 0:
            print("news_items 表为空，无需去重")
            return 0

        # 重复键 (title, publish_time) 的数量
        dup_keys = conn.execute("""
            SELECT TRIM(COALESCE(title,'')) AS tk, TRIM(COALESCE(publish_time,'')) AS pk, COUNT(*) AS cnt
            FROM news_items
            GROUP BY tk, pk
            HAVING COUNT(*) > 1
        """).fetchall()

        to_remove = sum(cnt - 1 for (_tk, _pk, cnt) in dup_keys)  # 每组保留 1 条
        unique_after = total - to_remove

        print(f"当前 news_items 总条数: {total}")
        print(f"重复 (title, publish_time) 组数: {len(dup_keys)}")
        print(f"将删除重复条数: {to_remove}")
        print(f"去重后条数: {unique_after}")

        if args.dry_run:
            if dup_keys:
                print("\n示例重复键（前 5 组）:")
                for tk, pk, c in dup_keys[:5]:
                    print(f"  title={str(tk)[:50]}... publish_time={pk} count={c}")
            return 0

        if to_remove == 0:
            print("无重复，无需写库")
            return 0

        # 建临时表：每组保留 ts 最大的一条
        conn.execute("""
            CREATE OR REPLACE TABLE news_items_dedup AS
            SELECT ts, symbol, source_site, source, title, content, url, keyword, tag,
                   publish_time, sentiment_score, sentiment_label
            FROM (
                SELECT *,
                       ROW_NUMBER() OVER (
                           PARTITION BY TRIM(COALESCE(title,'')), TRIM(COALESCE(publish_time,''))
                           ORDER BY ts DESC NULLS LAST
                       ) AS rn
                FROM news_items
            ) sub
            WHERE rn = 1
        """)
        conn.execute("DROP TABLE news_items")
        conn.execute("ALTER TABLE news_items_dedup RENAME TO news_items")
        conn.close()

        print("已删除重复记录并保留每组最新一条")
        return 0
    except Exception as e:
        print(f"执行失败: {e}")
        if conn is not None:
            conn.close()
        return 1


if __name__ == "__main__":
    sys.exit(main())
