"""Phase 2: Batch collect financial reports for first 100 A-share stocks by symbol."""
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "packages/financial-report/src"))

import duckdb
from financial_report.fetcher import (
    ensure_table,
    process_single_stock,
    STATEMENT_TYPES,
    _db_path,
)

def main():
    db_path = _db_path()
    print(f"数据库: {db_path}")
    print(f"报表类型: {', '.join(STATEMENT_TYPES)}")
    print()

    # Read symbols from file to avoid DB lock contention
    symbols_file = "/tmp/phase2_symbols.txt"
    if not os.path.exists(symbols_file):
        print(f"[错误] 找不到符号文件: {symbols_file}")
        return 1

    with open(symbols_file) as f:
        content = f.read().strip()

    symbols = [s.strip() for s in content.split(",") if s.strip()]
    if not symbols:
        print("[错误] 无有效符号", file=sys.stderr)
        return 1

    symbols = symbols[:100]

    print(f"Phase 2: 共 {len(symbols)} 只股票 (前 100 只按 symbol 排序)")
    print(f"区间: {symbols[0]} ... {symbols[-1]}")
    print()

    grand_total = 0

    from duckdb_write_lock import duckdb_write_lock

    with duckdb_write_lock(db_path=db_path) as resolved_path:
        conn = duckdb.connect(resolved_path)
        try:
            ensure_table(conn)
            for i, symbol in enumerate(symbols, 1):
                print(f"[{i}/{len(symbols)}] 处理股票: {symbol}", flush=True)
                total = process_single_stock(symbol, STATEMENT_TYPES, conn, dry_run=False)
                grand_total += total
                print(f"  -> 写入 {total} 行", flush=True)
                if i < len(symbols):
                    time.sleep(0.5)
            conn.commit()
        finally:
            conn.close()

    # Report per-statement counts
    with duckdb_write_lock(db_path=db_path) as resolved_path:
        conn = duckdb.connect(resolved_path)
        try:
            result = conn.execute(
                "SELECT statement_type, count(*) as cnt FROM financial_reports GROUP BY statement_type ORDER BY cnt DESC"
            ).fetchdf()
            print("\n=== 最终统计 (Phase 1 + Phase 2) ===")
            print(result.to_string(index=False))
            print(f"\n总行数: {result['cnt'].sum()}")
        finally:
            conn.close()

    return 0

if __name__ == "__main__":
    sys.exit(main())
