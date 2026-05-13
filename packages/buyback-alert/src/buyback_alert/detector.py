"""
detector.py — Consecutive drop detection from daily_bars.

For each stock in the stocks table, scan daily_bars ordered by trade_date
and find streaks where close < prev_close for N consecutive days (default 3).

Output: list of dicts with stock_code, stock_name, consecutive_drop_days,
        total_drop_pct, start_date, end_date.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import duckdb
from tqdm import tqdm


def detect_consecutive_drops(
    conn: duckdb.DuckDBPyConnection,
    *,
    min_days: int = 3,
    symbol: Optional[str] = None,
    dry_run: bool = False,
    trade_date_limit: Optional[int] = 120,
) -> List[Dict[str, Any]]:
    """Scan daily_bars for consecutive drop streaks.

    Parameters
    ----------
    conn : DuckDB connection.
    min_days : minimum consecutive drop days to report (default 3).
    symbol : optional stock code filter (e.g. '600519' or '600519.XSHG').
    dry_run : if True, only print results without returning full data.
    trade_date_limit : max trading days back from latest date to scan (default 120).

    Returns
    -------
    List of dicts with keys:
        stock_code, stock_name, consecutive_drop_days, total_drop_pct,
        start_date, end_date
    """
    # Get all stocks
    if symbol:
        sym_clean = symbol.replace(".XSHG", "").replace(".XSHE", "").replace(".BJ", "")
        stocks = conn.execute(
            "SELECT order_book_id, symbol, name FROM stocks WHERE symbol=? OR order_book_id=?",
            [sym_clean, symbol],
        ).fetchall()
    else:
        stocks = conn.execute(
            "SELECT order_book_id, symbol, name FROM stocks WHERE name IS NOT NULL AND name != '' AND type='CS'"
        ).fetchall()

    if not stocks:
        print("[detector] No stocks found")
        return []

    print(f"[detector] 共 {len(stocks)} 只股票，开始连跌检测（min_days={min_days}）")

    # Get the latest trade_date in daily_bars
    latest_date_row = conn.execute("SELECT MAX(trade_date) FROM daily_bars").fetchone()
    latest_date = latest_date_row[0] if latest_date_row else None
    if not latest_date:
        print("[detector] daily_bars is empty")
        return []

    results: List[Dict[str, Any]] = []

    for obid, sym, name in tqdm(stocks, desc="连跌检测"):
        obid_str = str(obid)
        name_str = str(name) if name else sym

        # Fetch close prices (most recent trade_date_limit days)
        rows = conn.execute(
            """SELECT trade_date, close FROM daily_bars
               WHERE order_book_id=? AND close IS NOT NULL AND close > 0
               ORDER BY trade_date DESC
               LIMIT ?""",
            [obid_str, trade_date_limit],
        ).fetchall()

        if len(rows) < min_days + 1:
            continue

        # Reverse to chronological
        rows = list(reversed(rows))

        # Scan for consecutive drops
        best: Optional[Dict[str, Any]] = None
        current_start_idx = 0
        current_days = 0

        for i in range(1, len(rows)):
            prev_close = float(rows[i - 1][1])
            cur_close = float(rows[i][1])
            cur_date = rows[i][0]

            if cur_close < prev_close:
                if current_days == 0:
                    current_start_idx = i - 1
                current_days += 1
            else:
                # End of streak
                if current_days >= min_days:
                    start_date = rows[current_start_idx][0]
                    end_date = rows[i - 1][0]
                    start_close = float(rows[current_start_idx][1])
                    end_close = float(rows[i - 1][1])
                    drop_pct = (end_close - start_close) / start_close * 100

                    # Keep the longest / most severe
                    if best is None or current_days > best["days"] or (
                        current_days == best["days"] and drop_pct < best["drop_pct"]
                    ):
                        best = {
                            "stock_code": sym,
                            "stock_name": name_str,
                            "consecutive_drop_days": current_days,
                            "total_drop_pct": round(drop_pct, 2),
                            "start_date": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)[:10],
                            "end_date": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)[:10],
                            "days": current_days,
                            "drop_pct": drop_pct,
                        }
                current_days = 0

        # Check if streak extends to the most recent bar
        if current_days >= min_days:
            start_date = rows[current_start_idx][0]
            end_date = rows[-1][0]
            start_close = float(rows[current_start_idx][1])
            end_close = float(rows[-1][1])
            drop_pct = (end_close - start_close) / start_close * 100

            if best is None or current_days > best["days"] or (
                current_days == best["days"] and drop_pct < best["drop_pct"]
            ):
                best = {
                    "stock_code": sym,
                    "stock_name": name_str,
                    "consecutive_drop_days": current_days,
                    "total_drop_pct": round(drop_pct, 2),
                    "start_date": start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)[:10],
                    "end_date": end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)[:10],
                    "days": current_days,
                    "drop_pct": drop_pct,
                }

        if best:
            if dry_run:
                print(
                    f"  [DRY-RUN] {best['stock_code']} {best['stock_name']}: "
                    f"连跌{best['consecutive_drop_days']}天, "
                    f"累计跌幅{best['total_drop_pct']:.2f}%, "
                    f"{best['start_date']} ~ {best['end_date']}"
                )
            results.append(best)

    print(f"[detector] 完成: 发现 {len(results)} 只股票连跌≥{min_days}天")
    return results
