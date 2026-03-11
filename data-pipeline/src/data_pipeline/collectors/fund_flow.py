"""个股资金流排名：主力净流入等，写入 a_stock_fundflow。"""
from __future__ import annotations

import datetime

def update_fundflow() -> int:
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from ..storage.duckdb_manager import get_conn, ensure_tables

    df = ak.stock_individual_fund_flow_rank(indicator="今日")
    if df is None or df.empty:
        return 0
    now = datetime.datetime.now()
    today = now.date()
    # 列名因 akshare 版本可能为 代码/名称/主力净流入 等
    df = df.copy()
    df["snapshot_time"] = now
    df["snapshot_date"] = today
    code_col = "代码" if "代码" in df.columns else "code"
    name_col = "名称" if "名称" in df.columns else "name"
    main_col = "主力净流入" if "主力净流入" in df.columns else "主力净流入-净额"
    if main_col not in df.columns:
        cand = [c for c in df.columns if "主力" in str(c) or "净流入" in str(c)]
        main_col = cand[0] if cand else None
    df = df.rename(columns={code_col: "code", name_col: "name"})
    if main_col:
        df = df.rename(columns={main_col: "main_net_inflow"})
    if "main_net_inflow" not in df.columns:
        df["main_net_inflow"] = 0.0
    cols = ["code", "name", "main_net_inflow", "snapshot_date", "snapshot_time"]
    out = df[[c for c in cols if c in df.columns]].copy()

    conn = get_conn()
    ensure_tables(conn)
    conn.register("tmp", out)
    conn.execute("""
        INSERT INTO a_stock_fundflow (code, name, main_net_inflow, snapshot_date, snapshot_time)
        SELECT code, name, main_net_inflow, snapshot_date, snapshot_time FROM tmp
    """)
    n = len(out)
    conn.close()
    return n
