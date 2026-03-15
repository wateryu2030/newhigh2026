"""涨停池：当日涨停标的，情绪周期/连板分析用。"""

from __future__ import annotations

import datetime as dt


def update_limitup() -> int:
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from ..storage.duckdb_manager import get_conn, ensure_tables

    df = ak.stock_zt_pool_em(date=dt.datetime.now().strftime("%Y%m%d"))
    if df is None or df.empty:
        return 0
    now = dt.datetime.now()
    df = df.copy()
    df["snapshot_time"] = now
    code_col = "代码" if "代码" in df.columns else "code"
    name_col = "名称" if "名称" in df.columns else "name"
    price_col = "最新价" if "最新价" in df.columns else "price"
    pct_col = "涨跌幅" if "涨跌幅" in df.columns else "change_pct"
    times_col = "连板数" if "连板数" in df.columns else "limit_up_times"
    df = df.rename(
        columns={
            code_col: "code",
            name_col: "name",
            price_col: "price",
            pct_col: "change_pct",
            times_col: "limit_up_times",
        }
    )
    for c in ["price", "change_pct", "limit_up_times"]:
        if c not in df.columns:
            df[c] = 0.0
    out = df[["code", "name", "price", "change_pct", "limit_up_times", "snapshot_time"]].copy()
    out = out.fillna(0)

    conn = get_conn()
    ensure_tables(conn)
    conn.register("tmp", out)
    conn.execute("""
        INSERT INTO a_stock_limitup (code, name, price, change_pct, limit_up_times, snapshot_time)
        SELECT code, name, price, change_pct, limit_up_times, snapshot_time FROM tmp
    """)
    n = len(out)
    conn.close()
    return n
