#!/usr/bin/env python3
"""
A 股/北交所数据完整性：检测 DuckDB 缺失区间，从 akshare/东方财富/北交所 自动拉取并写入本地 DuckDB。

与 OPENCLAW 数据循环配合：缺数据时自动补全，保证分析数据完整，供策略回测与进化使用。

用法（仓库根目录，已激活 .venv）：
  python scripts/ensure_ashare_data_completeness.py
  python scripts/ensure_ashare_data_completeness.py --symbols 600519,000001 --days 60
  python scripts/ensure_ashare_data_completeness.py --from-akshare-only   # 仅从 akshare 拉列表，不读 DuckDB
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data-engine", "src"))
sys.path.insert(0, os.path.join(ROOT, "core", "src"))


def _duckdb_path() -> str:
    from data_engine.connector_astock_duckdb import DEFAULT_NEWHIGH_DUCKDB_PATH

    return os.environ.get("NEWHIGH_DUCKDB_PATH", "").strip() or DEFAULT_NEWHIGH_DUCKDB_PATH


def _symbol_to_order_book_id(symbol: str) -> str:
    from data_engine.connector_astock_duckdb import _symbol_to_order_book_id as _ob

    return _ob(symbol)


def run(
    symbols: list[str] | None = None,
    days_back: int = 365,
    duckdb_path: str | None = None,
    from_akshare_only: bool = False,
    max_symbols: int = 500,
) -> dict:
    """
    补全逻辑：对每个标的取 DuckDB 中 max(trade_date)，若小于今日则从 akshare 拉取 [max+1, today] 并 INSERT。
    返回 {"filled": int, "skipped": int, "errors": int, "details": [...]}。
    """
    import duckdb
    from data_engine.connector_akshare import fetch_klines_akshare, get_stock_list_akshare
    from data_engine.connector_astock_duckdb import get_astock_duckdb_available, get_stocks_for_api

    path = duckdb_path or _duckdb_path()
    if not path or not os.path.isfile(path):
        return {
            "filled": 0,
            "skipped": 0,
            "errors": 1,
            "details": ["DuckDB not found: " + str(path)],
        }

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    end_date = datetime.now(timezone.utc).strftime("%Y%m%d")
    start_fallback = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y%m%d")

    if symbols:
        symbol_list = [s.strip().split(".", maxsplit=1)[0] or s.strip() for s in symbols if s.strip()]
        symbol_list = [s for s in symbol_list if 5 <= len(s) <= 8]
    elif from_akshare_only:
        try:
            rows = get_stock_list_akshare(include_bse=True)
            symbol_list = [r["symbol"].split(".", maxsplit=1)[0] for r in rows[:max_symbols]]
        except Exception:
            symbol_list = []
    else:
        if not get_astock_duckdb_available():
            try:
                rows = get_stock_list_akshare(include_bse=True)
                symbol_list = [r["symbol"].split(".", maxsplit=1)[0] for r in rows[:max_symbols]]
            except Exception:
                symbol_list = []
        else:
            try:
                rows = get_stocks_for_api()
                symbol_list = [r["symbol"].split(".", maxsplit=1)[0] for r in rows[:max_symbols]]
            except Exception:
                symbol_list = []

    if not symbol_list:
        return {"filled": 0, "skipped": 0, "errors": 0, "details": ["No symbols to fill"]}

    conn = duckdb.connect(path)
    filled, skipped, errors = 0, 0, 0
    details = []

    def _code_to_ob(c: str) -> str:
        suf = (
            ".SH"
            if c.startswith("6")
            else (".BSE" if (c.startswith(("4", "8", "9")) or len(c) == 8) else ".SZ")
        )
        return _symbol_to_order_book_id(c + suf)

    for code in symbol_list:
        try:
            ob = _code_to_ob(code)
            if not ob or "." not in ob:
                ob = (
                    code + ".XSHG"
                    if code.startswith("6")
                    else (
                        code + ".BSE"
                        if len(code) == 8 or code.startswith(("4", "8", "9"))
                        else code + ".XSHE"
                    )
                )
            cur = conn.execute(
                "SELECT MAX(trade_date) AS md FROM daily_bars WHERE order_book_id = ?",
                [ob],
            )
            row = cur.fetchone()
            max_date = row[0] if row and row[0] is not None else None
            if max_date is not None:
                if hasattr(max_date, "strftime"):
                    start_date = (max_date + timedelta(days=1)).strftime("%Y%m%d")
                else:
                    start_date = str(max_date).replace("-", "")[:8]
                    if len(start_date) == 8:
                        d = datetime.strptime(start_date, "%Y%m%d") + timedelta(days=1)
                        start_date = d.strftime("%Y%m%d")
                    else:
                        start_date = start_fallback
            else:
                start_date = start_fallback

            if start_date > end_date:
                skipped += 1
                continue

            klines = fetch_klines_akshare(
                symbol=code,
                start_date=start_date,
                end_date=end_date,
                period="daily",
                adjust="qfq",
            )
            if not klines:
                skipped += 1
                continue

            ob_id = _code_to_ob(code)
            if not ob_id:
                ob_id = ob
            for bar in klines:
                td = bar.timestamp.strftime("%Y-%m-%d")
                try:
                    conn.execute(
                        """
                        INSERT INTO daily_bars
                        (order_book_id, trade_date, adjust_type, open, high, low, close, volume, total_turnover, adjust_factor)
                        VALUES (?, ?::DATE, 'qfq', ?, ?, ?, ?, ?, ?, 1.0)
                        """,
                        [
                            ob_id,
                            td,
                            bar.open,
                            bar.high,
                            bar.low,
                            bar.close,
                            bar.volume or 0,
                            0.0,
                        ],
                    )
                except Exception:
                    pass  # 主键冲突或其它错误则跳过
            n = len(klines)
            filled += n
            details.append(f"{ob}: +{n} bars")
        except Exception as e:
            errors += 1
            details.append(f"{code}: error {e}")

    conn.close()
    return {"filled": filled, "skipped": skipped, "errors": errors, "details": details[:50]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Ensure A-share/BSE data completeness in DuckDB")
    parser.add_argument("--symbols", type=str, default=None, help="Comma-separated 6/8 digit codes")
    parser.add_argument(
        "--days", type=int, default=365, help="Days to look back when no existing data"
    )
    parser.add_argument("--duckdb", type=str, default=None, help="Path to quant_system.duckdb")
    parser.add_argument(
        "--from-akshare-only",
        action="store_true",
        help="Get symbol list only from akshare (A+北交所)",
    )
    parser.add_argument(
        "--max-symbols", type=int, default=500, help="Max symbols to process when using list"
    )
    args = parser.parse_args()

    symbols = args.symbols.split(",") if args.symbols else None
    result = run(
        symbols=symbols,
        days_back=args.days,
        duckdb_path=args.duckdb,
        from_akshare_only=args.from_akshare_only,
        max_symbols=args.max_symbols,
    )
    print("Filled:", result["filled"], "Skipped:", result["skipped"], "Errors:", result["errors"])
    for d in result["details"][:20]:
        print(" ", d)
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
