"""龙虎榜明细：游资席位/资金跟踪，写入 a_stock_longhubang。"""

from __future__ import annotations

import datetime as dt


def update_longhubang() -> int:
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from ..storage.duckdb_manager import get_conn, ensure_tables

    # 近期龙虎榜明细（可带 date 参数）
    try:
        df = ak.stock_lhb_detail_em(symbol="近一月")
    except Exception:
        try:
            df = ak.stock_lhb_detail_em()
        except Exception:
            return 0
    if df is None or df.empty:
        return 0
    now = dt.datetime.now()
    df = df.copy()
    df["snapshot_time"] = now
    code_col = "代码" if "代码" in df.columns else "code"
    name_col = "名称" if "名称" in df.columns else "name"
    date_col = "成交日期" if "成交日期" in df.columns else "lhb_date"
    net_col = "净买入" if "净买入" in df.columns else "net_buy"
    df = df.rename(
        columns={code_col: "code", name_col: "name", date_col: "lhb_date", net_col: "net_buy"}
    )
    for c in ["code", "name", "lhb_date", "net_buy"]:
        if c not in df.columns:
            df[c] = "" if c in ("code", "name") else None
    df["lhb_date"] = pd.to_datetime(df["lhb_date"], errors="coerce").dt.date
    out = df[["code", "name", "lhb_date", "net_buy", "snapshot_time"]].dropna(subset=["code"])
    out = out.fillna(0)

    conn = get_conn()
    ensure_tables(conn)
    conn.register("tmp", out)
    conn.execute("""
        INSERT INTO a_stock_longhubang (code, name, lhb_date, net_buy, snapshot_time)
        SELECT code, name, lhb_date, net_buy, snapshot_time FROM tmp
    """)
    n = len(out)
    conn.close()
    return n
