"""Phase 1: Batch collect financial reports for 10 specific A-share stocks."""
import sys
import os
import time

# Ensure PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages/financial-report/src"))

import duckdb
from financial_report.fetcher import (
    ensure_table,
    process_single_stock,
    STATEMENT_TYPES,
    _db_path,
)

# Phase 1 stocks
PHASE1_SYMBOLS = [
    "000001", "000002", "000651", "000858",
    "002415", "300750",
    "600036", "600519", "600887", "601318",
]

def main():
    db_path = _db_path()
    print(f"数据库: {db_path}")
    print(f"股票数量: {len(PHASE1_SYMBOLS)}")
    print(f"报表类型: {', '.join(STATEMENT_TYPES)}")
    print()

    # Use duckdb_write_lock for safe access
    from duckdb_write_lock import duckdb_write_lock

    grand_total = 0
    per_statement = {st: 0 for st in STATEMENT_TYPES}

    with duckdb_write_lock(db_path=db_path) as resolved_path:
        conn = duckdb.connect(resolved_path)
        try:
            ensure_table(conn)
            for i, symbol in enumerate(PHASE1_SYMBOLS, 1):
                print(f"[{i}/{len(PHASE1_SYMBOLS)}] 处理股票: {symbol}")
                total = process_single_stock(symbol, STATEMENT_TYPES, conn, dry_run=False)
                grand_total += total
                print(f"  -> 股票 {symbol} 完成, 写入 {total} 行")
                # Sleep 1 second between stocks to avoid rate limiting
                if i < len(PHASE1_SYMBOLS):
                    time.sleep(1)
            conn.commit()
        finally:
            conn.close()

    # Query per-statement counts
    with duckdb_write_lock(db_path=db_path) as resolved_path:
        conn = duckdb.connect(resolved_path)
        try:
            result = conn.execute(
                "SELECT statement_type, count(*) as cnt FROM financial_reports GROUP BY statement_type ORDER BY cnt DESC"
            ).fetchdf()
            print("\n=== Phase 1 完成统计 ===")
            print(result.to_string(index=False))
            print(f"\n总计: {grand_total} 行")
        finally:
            conn.close()

if __name__ == "__main__":
    main()
