#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检测 DuckDB 数据量是否满足要求；若不满足则自动拉取 A 股日线（断点续传）。
满足条件：至少 100 只标的、1 万条日线，且 stocks 与 daily_bars 一一对应。
"""
from __future__ import annotations
import argparse
import os
import sys
from typing import Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)
sys.path.insert(0, _ROOT)

# 达标阈值
MIN_STOCKS = 100
MIN_DAILY_BARS = 10_000


def get_duckdb_stats() -> Tuple[bool, int, int, int, str | None, str | None]:
    """
    检测 quant.duckdb 的 stocks 数、daily_bars 数、日期范围。
    :return: (是否满足要求, n_stocks, n_bars, n_symbols_with_bars, date_min, date_max)
    """
    duckdb_path = os.path.join(_ROOT, "data", "quant.duckdb")
    if not os.path.exists(duckdb_path):
        return False, 0, 0, 0, None, None
    try:
        import duckdb
        conn = duckdb.connect(duckdb_path, read_only=True)
        n_stocks = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
        n_bars = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
        r = conn.execute("SELECT MIN(trade_date), MAX(trade_date) FROM daily_bars").fetchone()
        date_min = str(r[0]) if r and r[0] else None
        date_max = str(r[1]) if r and r[1] else None
        n_symbols_with_bars = conn.execute("SELECT COUNT(DISTINCT order_book_id) FROM daily_bars").fetchone()[0]
        conn.close()
        ok = n_stocks >= MIN_STOCKS and n_bars >= MIN_DAILY_BARS and n_symbols_with_bars == n_stocks
        return ok, n_stocks, n_bars, n_symbols_with_bars, date_min, date_max
    except Exception as e:
        print(f"检测 DuckDB 失败: {e}", file=sys.stderr)
        return False, 0, 0, 0, None, None


def run_check(verbose: bool = True) -> bool:
    """执行检测并打印结果，返回是否满足要求。"""
    ok, n_stocks, n_bars, n_sym_bars, date_min, date_max = get_duckdb_stats()
    if verbose:
        print("========== DuckDB 数据量检测 ==========")
        print(f"  stocks:           {n_stocks} (要求 >= {MIN_STOCKS})")
        print(f"  daily_bars:      {n_bars} (要求 >= {MIN_DAILY_BARS})")
        print(f"  有日线的标的数:   {n_sym_bars}")
        print(f"  日期范围:        {date_min or '—'} ~ {date_max or '—'}")
        if ok:
            print("  结论: ✅ 满足 K 线、扫描、回测、AI 推荐等需求。")
        else:
            print("  结论: ❌ 数据不足，将触发自动拉取（断点续传）。")
        print()
    return ok


def run_fetch(days: int = 365 * 2, delay: float = 0.12) -> int:
    """全量 A 股日线拉取（跳过已有数据），返回成功拉取只数。"""
    from datetime import datetime, timedelta
    from database.data_fetcher import DataFetcher
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    print(f"开始拉取 A 股日线: {start_date} ~ {end_date}（跳过已有数据，断点续传）")
    fetcher = DataFetcher()
    n = fetcher.fetch_all_a_stocks(
        start_date=start_date,
        end_date=end_date,
        delay=delay,
        skip_existing=True,
    )
    print(f"拉取完成: 本次成功 {n} 只。")
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="检测 DuckDB 数据量，不足时自动拉取")
    parser.add_argument("--no-fetch", action="store_true", help="仅检测，不自动拉取")
    parser.add_argument("--days", type=int, default=365 * 2, help="拉取历史天数（默认 2 年）")
    parser.add_argument("--delay", type=float, default=0.12, help="每只请求间隔(秒)")
    args = parser.parse_args()

    if run_check(verbose=True):
        return 0
    if args.no_fetch:
        return 1
    run_fetch(days=args.days, delay=args.delay)
    print("重新检测...")
    if run_check(verbose=True):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
