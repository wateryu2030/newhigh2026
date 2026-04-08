#!/usr/bin/env python3
"""刷新终端用市场快照：实时行情、涨停池、资金流。项目根执行，依赖 .venv 与 .env。"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
for d in (
    str(ROOT),
    str(ROOT / "data-pipeline" / "src"),
    str(ROOT / "lib"),
):
    if os.path.isdir(d) and d not in sys.path:
        sys.path.insert(0, d)

try:
    from newhigh_env import load_dotenv_if_present
except ImportError:
    load_dotenv_if_present = None
else:
    load_dotenv_if_present(ROOT)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh realtime / limitup / fundflow snapshots.")
    parser.add_argument("--skip-realtime", action="store_true")
    parser.add_argument("--skip-limitup", action="store_true")
    parser.add_argument("--skip-fundflow", action="store_true")
    args = parser.parse_args(argv)

    from data_pipeline.collectors.fund_flow import update_fundflow
    from data_pipeline.collectors.limit_up import update_limitup
    from data_pipeline.collectors.realtime_quotes import update_realtime_quotes
    from data_pipeline.storage.duckdb_manager import ensure_tables, get_conn

    print("[refresh] ensure_tables …")
    c = get_conn(read_only=False)
    ensure_tables(c)
    c.close()

    if not args.skip_limitup:
        n = update_limitup()
        print(f"[refresh] a_stock_limitup rows: {n}")
    else:
        print("[refresh] skip limitup")

    if not args.skip_realtime:
        n = update_realtime_quotes()
        print(f"[refresh] a_stock_realtime rows: {n}")
    else:
        print("[refresh] skip realtime")

    if not args.skip_fundflow:
        n = update_fundflow()
        print(f"[refresh] a_stock_fundflow rows: {n}")
    else:
        print("[refresh] skip fundflow")

    print("[refresh] done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
