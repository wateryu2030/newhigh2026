"""A股股票池：沪A+深A+北交所，来自 akshare。"""

from __future__ import annotations


def update_stock_list() -> int:
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from ..storage.duckdb_manager import get_conn, ensure_tables

    df = ak.stock_info_a_code_name()
    if df is None or df.empty:
        return 0
    # 列名通常为 code, name；部分版本为 代码, 名称
    if "code" not in df.columns and "代码" in df.columns:
        df = df.rename(columns={"代码": "code", "名称": "name"})
    df = df[["code", "name"]] if "name" in df.columns else df[["code"]].assign(name=df["code"])
    df = df.dropna(subset=["code"]).drop_duplicates(subset=["code"])

    conn = get_conn()
    ensure_tables(conn)
    conn.execute("DELETE FROM a_stock_basic")
    conn.register("df", df)
    conn.execute("INSERT INTO a_stock_basic SELECT code, name FROM df")
    n = conn.execute("SELECT COUNT(*) FROM a_stock_basic").fetchone()[0]
    conn.close()
    return int(n)
