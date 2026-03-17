"""
读取 newhigh 统一 DuckDB（data/quant_system.duckdb），与 data_pipeline 共用同一库。
表结构：daily_bars, stocks, news_items（与 astock 一致）；数据可由 copy_astock_duckdb_to_newhigh.py 写入。
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Tuple

from core import OHLCV
from core.data_service.db import get_conn as get_db_conn, get_astock_duckdb_available as check_astock_available


def _order_book_id_to_symbol(order_book_id: str) -> str:
    """astock order_book_id -> newhigh 统一 symbol。600519.XSHG -> 600519.SH, 000001.XSHE -> 000001.SZ."""
    ob = (order_book_id or "").strip()
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


def _symbol_to_order_book_id(symbol: str) -> str:
    """newhigh symbol 或 6/8 位代码 -> astock order_book_id。600519.SH->600519.XSHG，830799.BSE->830799.BSE。"""
    s = (symbol or "").strip().split(".", maxsplit=1)[0]
    if not s or len(s) < 5 or len(s) > 8:
        return symbol or ""
    if s.startswith("6"):
        return f"{s}.XSHG"
    if s.startswith(("4", "8", "9")) or len(s) == 8:
        return f"{s}.BSE"
    return f"{s}.XSHE"


# 使用 core.data_service.db 中的统一函数
def _get_conn(read_only: bool = True):
    """获取 newhigh 本地 DuckDB 连接（代理到 core.data_service.db.get_conn）。"""
    return get_db_conn(read_only=read_only)


def get_astock_duckdb_available() -> bool:
    """检查 newhigh 本地 A 股 DuckDB 是否可用（代理到 core.data_service.db.get_astock_duckdb_available）。"""
    return check_astock_available()


def fetch_klines_from_astock_duckdb(
    symbol: str,
    start_date: str | None = None,
    end_date: str | None = None,
    adjust_type: str = "qfq",
    limit: int | None = None,
    recent_first: bool = False,
    conn: Any = None,
) -> List[OHLCV]:
    """
    从 newhigh 本地 DuckDB 读取 A 股日线，转为 List[OHLCV]。
    symbol: 6 位代码或 600519.SH / 000001.SZ
    start_date/end_date: YYYY-MM-DD 或 YYYYMMDD
    adjust_type: qfq / hfq
    limit: 条数；recent_first=True 时取最近 N 条（按日期倒序取再按正序返回），否则取最早 N 条
    conn: 可选，传入已打开的 DuckDB 只读连接时复用该连接（避免多连接锁冲突）；调用方负责关闭。
    """
    if conn is None:
        conn = _get_conn()
    if conn is None:
        return []
    ob = _symbol_to_order_book_id(symbol)
    if not ob:
        return []

    # 归一化日期
    def _norm(d: str | None) -> str | None:
        if not d:
            return None
        d = d.replace("-", "")[:8]
        if len(d) == 8:
            return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
        return None

    start = _norm(start_date)
    end = _norm(end_date)
    base = (
        "SELECT order_book_id, trade_date, open, high, low, close, volume FROM daily_bars "
        "WHERE order_book_id = ? AND adjust_type = ?"
    )
    params: List[Any] = [ob, adjust_type]
    if start:
        base += " AND trade_date >= ?"
        params.append(start)
    if end:
        base += " AND trade_date <= ?"
        params.append(end)
    if limit is not None and limit > 0 and recent_first:
        sql = f"SELECT * FROM ({base} ORDER BY trade_date DESC LIMIT {int(limit)}) AS t ORDER BY trade_date"
    else:
        sql = base + " ORDER BY trade_date"
        if limit is not None and limit > 0:
            sql += f" LIMIT {int(limit)}"
    try:
        df = conn.execute(sql, params).fetchdf()
    except Exception:
        return []
    if df is None or df.empty:
        return []
    out_symbol = _order_book_id_to_symbol(ob)
    result = []
    for _, row in df.iterrows():
        try:
            td = row["trade_date"]
            if hasattr(td, "to_pydatetime"):
                ts = td.to_pydatetime()
            elif isinstance(td, str):
                ts = dt.datetime.strptime(td[:10], "%Y-%m-%d")
            else:
                ts = dt.datetime.now(dt.timezone.utc)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=dt.timezone.utc)
            result.append(
                OHLCV(
                    symbol=out_symbol,
                    timestamp=ts,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row["volume"] or 0),
                    interval="1d",
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return result


def get_stocks_from_astock_duckdb() -> List[Tuple[str, str, str]]:
    """从 newhigh 本地 stocks 表读取 (order_book_id, symbol, name)。若 stocks 为空则从 daily_bars 去重。"""
    conn = _get_conn()
    if conn is None:
        return []
    try:
        df = conn.execute("SELECT order_book_id, symbol, name FROM stocks").fetchdf()
        if df is not None and not df.empty:
            return [
                (
                    str(row["order_book_id"]),
                    str(row.get("symbol") or row["order_book_id"]),
                    str(row.get("name") or ""),
                )
                for _, row in df.iterrows()
            ]
    except Exception:
        pass
    try:
        df = conn.execute(
            "SELECT DISTINCT order_book_id FROM daily_bars ORDER BY order_book_id"
        ).fetchdf()
        if df is not None and not df.empty:
            return [
                (ob, ob.split(".", maxsplit=1)[0], "")
                for ob in df["order_book_id"].astype(str).tolist()
            ]
    except Exception:
        pass
    return []


def get_stocks_for_api() -> List[Dict[str, Any]]:
    """供 Gateway/前端使用：返回 [{ symbol, name }]，symbol 已统一为 600519.SH / 000001.SZ。"""
    rows = get_stocks_from_astock_duckdb()
    out = []
    for ob, _code, name in rows:
        unified = _order_book_id_to_symbol(ob)
        out.append({"symbol": unified, "name": name or unified.split(".", maxsplit=1)[0]})
    return out


def get_duckdb_data_status() -> Dict[str, Any]:
    """供 Gateway/前端「数据状态」展示：标的数、日线条数、日期范围。"""
    conn = _get_conn()
    if conn is None:
        return {"stocks": 0, "daily_bars": 0, "date_min": None, "date_max": None}
    try:
        stocks = conn.execute("SELECT COUNT(*) FROM stocks").fetchone()
        stocks_n = int(stocks[0]) if stocks else 0
        if stocks_n == 0:
            df = conn.execute("SELECT DISTINCT order_book_id FROM daily_bars").fetchdf()
            stocks_n = len(df) if df is not None and not df.empty else 0
        bars = conn.execute(
            "SELECT COUNT(*) AS n, MIN(trade_date) AS dmin, MAX(trade_date) AS dmax FROM daily_bars"
        ).fetchone()
        if bars:
            return {
                "stocks": stocks_n,
                "daily_bars": int(bars[0]) if bars[0] is not None else 0,
                "date_min": str(bars[1])[:10] if bars[1] else None,
                "date_max": str(bars[2])[:10] if bars[2] else None,
            }
    except Exception:
        pass
    return {"stocks": 0, "daily_bars": 0, "date_min": None, "date_max": None}


def get_news_from_astock_duckdb(
    symbol: str | None = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """从 newhigh 本地 news_items 表读取新闻。symbol 可选（6 位或 600519.SH）；为空则全部。"""
    conn = _get_conn()
    if conn is None:
        return []
    try:
        if symbol:
            code = (symbol or "").strip().split(".", maxsplit=1)[0]
            if len(code) == 6:
                sql = "SELECT symbol, source_site, source, title, content, url, keyword, tag, publish_time, sentiment_score, sentiment_label FROM news_items WHERE symbol = ? OR symbol LIKE ? ORDER BY publish_time DESC LIMIT ?"
                params = [code, f"{code}.%", limit]
            else:
                sql = "SELECT symbol, source_site, source, title, content, url, keyword, tag, publish_time, sentiment_score, sentiment_label FROM news_items ORDER BY publish_time DESC LIMIT ?"
                params = [limit]
        else:
            sql = "SELECT symbol, source_site, source, title, content, url, keyword, tag, publish_time, sentiment_score, sentiment_label FROM news_items ORDER BY publish_time DESC LIMIT ?"
            params = [limit]
        df = conn.execute(sql, params).fetchdf()
    except Exception:
        return []
    if df is None or df.empty:
        return []
    return df.to_dict("records")
