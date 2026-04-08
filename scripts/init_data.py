#!/usr/bin/env python3
# Auto-fixed by Cursor on 2026-04-02: optional bulk download to Parquet + metadata.
"""
初始化/更新本地 Parquet 数据目录（不替代 DuckDB 主流程）。
用法（仓库根）：
  python scripts/init_data.py --quick
  python scripts/init_data.py --us SPY QQQ --years 3
  python scripts/init_data.py --cn 000001 600519 --years 2

需要：pandas pyarrow；可选 yfinance、akshare、pandas_datareader（FRED）。
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
for sub in ("lib", "data-pipeline/src"):
    p = ROOT / sub
    if p.is_dir() and str(p) not in sys.path:
        sys.path.insert(0, str(p))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="仅写元数据 + 下载 1 只美股日线样例")
    parser.add_argument("--us", nargs="*", default=[], help="美股代码 yfinance")
    parser.add_argument("--cn", nargs="*", default=[], help="A 股 6 位 akshare")
    parser.add_argument("--years", type=int, default=5)
    args = parser.parse_args()

    try:
        from lib.data_fetcher import (
            DEFAULT_PARQUET_ROOT,
            download_daily,
            save_to_parquet,
            write_metadata,
        )
    except ImportError as e:
        print("import failed:", e)
        return 1

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=365 * max(1, args.years))
    start_s, end_s = str(start), str(end)
    root = DEFAULT_PARQUET_ROOT
    root.mkdir(parents=True, exist_ok=True)

    written = []
    symbols = list(args.us) + list(args.cn)
    if args.quick:
        symbols = ["SPY"]

    for sym in symbols:
        try:
            df = download_daily(sym, start_s, end_s)
            if df is None or df.empty:
                continue
            safe = sym.replace(".", "_")
            path = root / "daily" / safe / f"{start_s}_{end_s}.parquet"
            save_to_parquet(df, path)
            written.append(str(path))
        except Exception as ex:
            print(sym, ex)

    # FRED DGS10 optional
    rf_path = root / "macro" / "dgs10.parquet"
    try:
        import pandas_datareader.data as web

        rf_path.parent.mkdir(parents=True, exist_ok=True)
        s = web.DataReader("DGS10", "fred", start, end)
        save_to_parquet(s.reset_index(), rf_path)
        written.append(str(rf_path))
    except Exception:
        pass

    write_metadata(
        root,
        {
            "symbols": symbols,
            "rows_written": written,
            "note": "A-share full market 5y via akshare should use backfill_a_stock_daily + DuckDB; this script is for Parquet sidecar.",
        },
    )
    print("ok", len(written), "files under", root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
