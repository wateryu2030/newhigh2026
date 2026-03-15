"""Market 数据：标的列表、市场概览，来自 DuckDB stocks / daily_bars。"""

from __future__ import annotations

from typing import Any, Dict, List

from .db import get_conn


def _order_book_id_to_ts_code(ob: str) -> str:
    """与 data_engine 一致：600519.XSHG -> 600519.SH, 000001.XSHE -> 000001.SZ"""
    ob = (ob or "").strip()
    if "." in ob:
        code, market = ob.split(".", 1)
        if market.upper() == "XSHG":
            return f"{code}.SH"
        if market.upper() == "XSHE":
            return f"{code}.SZ"
        if market.upper() == "BSE":
            return f"{code}.BSE"
        return f"{code}.{market}"
    return ob


def get_stock_list(limit: int = 100) -> List[Dict[str, Any]]:
    """返回 A 股标的列表，供 /api/stocks。字段：ts_code, name, industry（无则空串）。"""
    conn = get_conn()
    if conn is None:
        return []
    try:
        # stocks 表：order_book_id, symbol, name, market, ...
        df = conn.execute(
            "SELECT order_book_id, symbol, name FROM stocks ORDER BY order_book_id LIMIT ?",
            [limit],
        ).fetchdf()
        if df is None or df.empty:
            return []
        out = []
        for _, row in df.iterrows():
            ob = str(row.get("order_book_id", ""))
            ts_code = _order_book_id_to_ts_code(ob)
            name = str(row.get("name") or row.get("symbol") or ts_code.split(".", maxsplit=1)[0])
            out.append({"ts_code": ts_code, "name": name, "industry": ""})
        return out
    except Exception:
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_market_summary() -> Dict[str, Any]:
    """市场概览，供 /api/market/summary 与 Dashboard。"""
    conn = get_conn()
    if conn is None:
        return {
            "total_stocks": 0,
            "market": "A-share",
            "daily_bars": 0,
            "date_min": None,
            "date_max": None,
        }
    try:
        total = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()
        total_stocks = int(total[0]) if total else 0
        if total_stocks == 0:
            try:
                distinct = conn.execute(
                    "SELECT COUNT(DISTINCT order_book_id) FROM daily_bars"
                ).fetchone()
                total_stocks = int(distinct[0]) if distinct and distinct[0] is not None else 0
            except Exception:
                pass
        bars = conn.execute(
            "SELECT COUNT(*) AS n, MIN(trade_date) AS dmin, MAX(trade_date) AS dmax FROM daily_bars"
        ).fetchone()
        daily_bars = int(bars[0]) if bars and bars[0] is not None else 0
        date_min = str(bars[1])[:10] if bars and bars[1] else None
        date_max = str(bars[2])[:10] if bars and bars[2] else None
        return {
            "total_stocks": total_stocks,
            "market": "A-share",
            "daily_bars": daily_bars,
            "date_min": date_min,
            "date_max": date_max,
        }
    except Exception:
        return {
            "total_stocks": 0,
            "market": "A-share",
            "daily_bars": 0,
            "date_min": None,
            "date_max": None,
        }
    finally:
        try:
            conn.close()
        except Exception:
            pass
