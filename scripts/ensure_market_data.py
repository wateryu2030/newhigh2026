#!/usr/bin/env python3
"""
自动化填充 quant_system.duckdb，保证有足够数据量支撑情绪周期、游资席位、主线题材等分析。
顺序：股票池 → 日K线(批量) → 涨停池/龙虎榜/资金流 → 可选实时行情。
可单独运行或由 run_full_cycle.py 调用。
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ["data-pipeline/src", "core/src"]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)


def _ensure_tables() -> None:
    from data_pipeline.storage.duckdb_manager import get_conn, ensure_tables

    conn = get_conn(read_only=False)
    ensure_tables(conn)
    conn.close()


def _update_stock_list() -> int:
    from data_pipeline.collectors.stock_list import update_stock_list

    return update_stock_list()


def _update_daily_kline_batch(
    days_back: int = 250,
    max_symbols: int = 800,
    delay_seconds: float = 0.15,
) -> tuple[int, int]:
    from data_pipeline.storage.duckdb_manager import get_conn
    from data_pipeline.collectors.daily_kline import update_daily_kline

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")

    conn = get_conn(read_only=False)
    df = conn.execute(
        "SELECT code FROM a_stock_basic ORDER BY code LIMIT ?",
        [max_symbols],
    ).fetchdf()
    conn.close()
    if df is None or df.empty:
        return 0, 0

    codes = df["code"].astype(str).str.split(".").str[0].tolist()
    codes = [c for c in codes if c and len(c) >= 5]
    total_bars = 0
    ok = 0
    for i, code in enumerate(codes):
        try:
            n = update_daily_kline(code, start_date=start_date, end_date=end_date)
            if n > 0:
                total_bars += n
                ok += 1
        except Exception as e:
            if (i + 1) % 100 == 0 or i < 3:
                print(f"  kline {code}: {e}")
        if delay_seconds > 0:
            time.sleep(delay_seconds)
    return ok, total_bars


def _update_limitup() -> int:
    from data_pipeline.collectors.limit_up import update_limitup

    return update_limitup()


def _update_longhubang() -> int:
    from data_pipeline.collectors.longhubang import update_longhubang

    return update_longhubang()


def _update_fundflow() -> int:
    try:
        from data_pipeline.collectors.fund_flow import update_fundflow
        return update_fundflow()
    except Exception:
        # 东方财富资金流接口可能网络受限，降级返回 0
        return 0


def _update_realtime() -> int:
    try:
        from data_pipeline.collectors.realtime_quotes import update_realtime_quotes
        return update_realtime_quotes()
    except Exception:
        # 东方财富实时行情接口可能网络受限，降级返回 0
        return 0


def run(
    days_back: int = 250,
    max_symbols: int = 800,
    delay_seconds: float = 0.15,
    skip_kline: bool = False,
    skip_realtime: bool = True,
) -> dict:
    """
    执行顺序：建表 → 股票池 → 日K(可选) → 涨停/龙虎榜/资金流 → 实时(可选)。
    返回各步骤写入条数或统计。
    """
    result = {
        "stock_list": 0,
        "kline_stocks": 0,
        "kline_bars": 0,
        "limitup": 0,
        "longhubang": 0,
        "fundflow": 0,
        "realtime": 0,
    }

    print("Ensuring quant_system.duckdb tables...")
    _ensure_tables()

    print("Updating stock list (a_stock_basic)...")
    result["stock_list"] = _update_stock_list()
    print(f"  -> {result['stock_list']} symbols")

    if not skip_kline and result["stock_list"] > 0:
        print(f"Updating daily klines (last {days_back} days, max {max_symbols} symbols)...")
        ok, total = _update_daily_kline_batch(
            days_back=days_back,
            max_symbols=max_symbols,
            delay_seconds=delay_seconds,
        )
        result["kline_stocks"] = ok
        result["kline_bars"] = total
        print(f"  -> {ok} symbols, {total} bars")

    print("Updating limit-up pool...")
    result["limitup"] = _update_limitup()
    print(f"  -> {result['limitup']} rows")

    print("Updating longhubang...")
    result["longhubang"] = _update_longhubang()
    print(f"  -> {result['longhubang']} rows")

    print("Updating fund flow...")
    result["fundflow"] = _update_fundflow()
    print(f"  -> {result['fundflow']} rows")

    if not skip_realtime:
        print("Updating realtime quotes...")
        result["realtime"] = _update_realtime()
        print(f"  -> {result['realtime']} rows")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fill quant_system.duckdb for AI analysis (emotion/hotmoney/sector)."
    )
    parser.add_argument(
        "--days", type=int, default=250, help="Days of history for daily klines (default 250)"
    )
    parser.add_argument(
        "--max-symbols", type=int, default=800, help="Max symbols to fetch klines for (default 800)"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Delay between kline requests in seconds (default 0.15)",
    )
    parser.add_argument(
        "--skip-kline",
        action="store_true",
        help="Skip daily kline batch (only list + limitup + longhubang + fundflow)",
    )
    parser.add_argument("--realtime", action="store_true", help="Also update realtime quotes")
    args = parser.parse_args()

    run(
        days_back=args.days,
        max_symbols=args.max_symbols,
        delay_seconds=args.delay,
        skip_kline=args.skip_kline,
        skip_realtime=not args.realtime,
    )
    print("ensure_market_data done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
