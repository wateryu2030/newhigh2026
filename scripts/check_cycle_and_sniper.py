#!/usr/bin/env python3
"""
自动化执行并检查：跑一轮终端（扫描 + 游资狙击 + AI + 融合信号），
检查 market_emotion / sniper_candidates / trade_signals 是否有数据。
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
for d in [
    "data-pipeline/src",
    "market-scanner/src",
    "ai-models/src",
    "strategy-engine/src",
    "core/src",
]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def run_cycle() -> None:
    """执行终端单轮（含游资狙击）。"""
    from run_terminal_loop import main

    main()


def check() -> dict:
    """检查各表是否有数据，返回 { table: count }。"""
    try:
        from data_pipeline.storage.duckdb_manager import get_conn, get_db_path

        if not os.path.isfile(get_db_path()):
            return {"db": "missing"}
        conn = get_conn(read_only=True)
        out = {}
        for table in [
            "market_emotion",
            "sniper_candidates",
            "trade_signals",
            "market_signals",
            "a_stock_limitup",
        ]:
            try:
                row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
                out[table] = int(row[0]) if row and row[0] is not None else 0
            except Exception:
                out[table] = -1
        conn.close()
        return out
    except Exception as e:
        return {"error": str(e)}


def main() -> int:
    print("Running terminal loop (scanner + sniper + AI + fusion)...")
    run_cycle()
    print("Checks:")
    counts = check()
    for k, v in counts.items():
        print(f"  {k}: {v}")
    ok = counts.get("sniper_candidates", -1) >= 0 and (
        counts.get("market_emotion", 0) > 0
        or counts.get("trade_signals", 0) > 0
        or counts.get("sniper_candidates", 0) > 0
    )
    print(
        "Cycle + check done."
        if ok
        else "Cycle done; some tables empty (run ensure_market_data first?)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
