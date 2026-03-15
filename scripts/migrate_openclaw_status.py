#!/usr/bin/env python3
"""
OpenClaw 进化与 Skill 状态表结构迁移：为 system_status 增加 evolution/skill 字段，新建 skill_stats、evolution_tasks。
执行一次即可：python scripts/migrate_openclaw_status.py
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

for _d in ["data-pipeline/src", "core/src"]:
    _p = os.path.join(ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> None:
    from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

    conn = get_conn(read_only=False)
    ensure_tables(conn)

    # 1. system_status 新增列（已存在则跳过）
    for col_def in [
        "evolution_task_id VARCHAR",
        "evolution_status VARCHAR",
        "evolution_result VARCHAR",
        "skill_call_count INTEGER DEFAULT 0",
        "skill_last_call_time TIMESTAMP",
    ]:
        col_name = col_def.split()[0]
        try:
            conn.execute(f"ALTER TABLE system_status ADD COLUMN {col_def}")
            print(f"  system_status: added column {col_name}")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"  system_status: column {col_name} already exists")
            else:
                raise

    # 2. skill_stats 单行表：总调用次数、最近调用时间
    conn.execute("""
        CREATE TABLE IF NOT EXISTS skill_stats (
            call_count INTEGER DEFAULT 0,
            last_call_time TIMESTAMP
        )
    """)
    n = conn.execute("SELECT COUNT(*) FROM skill_stats").fetchone()[0]
    if n == 0:
        conn.execute("INSERT INTO skill_stats (call_count, last_call_time) VALUES (0, NULL)")
        print("  skill_stats: inserted initial row")
    else:
        print("  skill_stats: table ready")

    # 3. evolution_tasks：最近进化任务
    conn.execute("""
        CREATE TABLE IF NOT EXISTS evolution_tasks (
            task_id VARCHAR PRIMARY KEY,
            status VARCHAR NOT NULL,
            result VARCHAR,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("  evolution_tasks: table ready")

    conn.close()
    print("OpenClaw 状态迁移完成。")


if __name__ == "__main__":
    main()
