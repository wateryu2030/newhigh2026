#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DuckDB 数据完整性检查：确认 quant.duckdb 满足 K 线、扫描、回测、AI 推荐等需求。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)


def main():
    duckdb_path = os.path.join(_ROOT, "data", "quant.duckdb")
    print("========== DuckDB 数据完整性检查 ==========\n")

    if not os.path.exists(duckdb_path):
        print("❌ quant.duckdb 不存在")
        return 1

    import duckdb
    conn = duckdb.connect(duckdb_path, read_only=True)

    # 表
    tables = [r[0] for r in conn.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()]
    print("DuckDB 表:", ", ".join(tables))

    # stocks
    n_stocks = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()[0]
    print(f"\nstocks: {n_stocks} 行")
    sample = conn.execute("SELECT order_book_id, symbol, name FROM stocks LIMIT 2").fetchall()
    print("  样例:", sample)

    # daily_bars
    n_bars = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
    r = conn.execute("SELECT MIN(trade_date), MAX(trade_date) FROM daily_bars").fetchone()
    print(f"\ndaily_bars: {n_bars} 行, 日期 {r[0]} ~ {r[1]}")
    n_symbols_with_bars = conn.execute("SELECT COUNT(DISTINCT order_book_id) FROM daily_bars").fetchone()[0]
    print(f"  有日线的标的数: {n_symbols_with_bars}")

    # 一致性：stocks 与 daily_bars 的 order_book_id
    stocks_id = set(r[0] for r in conn.execute("SELECT order_book_id FROM stocks").fetchall())
    bars_id = set(r[0] for r in conn.execute("SELECT DISTINCT order_book_id FROM daily_bars").fetchall())
    only_stocks = stocks_id - bars_id
    only_bars = bars_id - stocks_id
    if only_stocks or only_bars:
        print(f"  ⚠ 仅在 stocks: {len(only_stocks)}, 仅在 daily_bars: {len(only_bars)}")
    else:
        print("  ✅ 所有 stocks 均在 daily_bars 有数据，无孤立标的")

    conn.close()

    # 需求结论
    print("\n--- 是否满足要求 ---")
    ok = n_stocks >= 100 and n_bars >= 10000 and n_symbols_with_bars == n_stocks
    if ok:
        print("  ✅ DuckDB 数据完整，满足 K 线、扫描、回测、AI 推荐等接口需求。")
    else:
        print("  ❌ 数据不足：需至少约 100 只标的、1 万条日线，且 stocks 与 daily_bars 一致。")
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
