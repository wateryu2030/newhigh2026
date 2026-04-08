#!/usr/bin/env python3
"""一键同步 quant_system.duckdb 终端所需快照：股票池 → 涨停 → 现货(新浪/日K) → 狙击候选。
在项目根执行: .venv/bin/python scripts/sync_duckdb_market_one_shot.py
依赖: .env 中 QUANT_SYSTEM_DUCKDB_PATH；可选 REALTIME_ENABLE_EM=1 启用东财分页（默认关）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
_root_s = str(ROOT)
if _root_s not in sys.path:
    sys.path.insert(0, _root_s)
for d in (
    "data-pipeline/src",
    "scanner/src",
    "lib",
    "core/src",
):
    p = str(ROOT / d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

try:
    from newhigh_env import load_dotenv_if_present
except ImportError:
    load_dotenv_if_present = None
else:
    load_dotenv_if_present(ROOT)


def main() -> int:
    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn
    from data_pipeline.collectors.stock_list import update_stock_list
    from data_pipeline.collectors.limit_up import update_limitup
    from data_pipeline.collectors.realtime_quotes import update_realtime_quotes

    print("[sync] ensure_tables …")
    c = get_conn(read_only=False)
    ensure_tables(c)
    c.close()

    n = update_stock_list()
    print(f"[sync] a_stock_basic: {n}")
    n = update_limitup()
    print(f"[sync] a_stock_limitup: {n}")
    n = update_realtime_quotes()
    print(f"[sync] a_stock_realtime: {n}")

    try:
        from market_scanner import run_sniper

        m = run_sniper(min_score=0.7, top_n=50)
        print(f"[sync] sniper_candidates rows: {m}")
    except Exception as e:
        print("[sync] run_sniper skipped:", e)

    print("[sync] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
