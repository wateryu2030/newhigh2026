"""个股资金流排名：主力净流入等，写入 a_stock_fundflow。"""

from __future__ import annotations

import datetime as dt


def update_fundflow(max_retries: int = 3) -> int:
    """
    采集资金流数据

    Args:
        max_retries: 最大重试次数（网络错误时）

    Returns:
        采集条数，失败返回 0
    """
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from ..storage.duckdb_manager import get_conn, ensure_tables

    # 网络重试逻辑
    df = None
    for attempt in range(max_retries):
        try:
            df = ak.stock_individual_fund_flow_rank(indicator="今日")
            if df is not None and not df.empty:
                break
        except Exception as e:
            if attempt < max_retries - 1:
                import time
                wait_time = (attempt + 1) * 2  # 2s, 4s, 6s
                print(f"  资金流采集失败 (尝试 {attempt+1}/{max_retries}): {e}")
                print(f"  {wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"  资金流采集失败，已达最大重试次数：{e}")
                return 0

    if df is None or df.empty:
        return 0
    now = dt.datetime.now()
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
