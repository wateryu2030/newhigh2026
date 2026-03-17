"""A股股票池：沪A+深A+北交所，来自 akshare。"""

from __future__ import annotations

import time


def update_stock_list() -> int:
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from ..storage.duckdb_manager import get_conn, ensure_tables

    # 尝试获取 A 股股票池（沪A+深A），不强制要求北交所数据
    try:
        df = ak.stock_info_a_code_name()
    except Exception as e:
        print(f"A股股票池获取失败（可能北交所连接问题）: {e}")
        # 降级方案：分别获取沪A和深A
        try:
            print("尝试降级：分别获取沪A和深A...")
            df_sh = ak.stock_info_sh_app()
            df_sz = ak.stock_info_sz_a()
            df = pd.concat([df_sh, df_sz], ignore_index=True)
            # renames
            if "证券代码" in df.columns:
                df = df.rename(columns={"证券代码": "code", "证券简称": "name"})
        except Exception as e2:
            print(f"降级方案也失败: {e2}")
            return 0

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
    # 只插入 code 和 name，避免与后续 ALTER 添加的 sector 列冲突
    conn.register("df", df)
    conn.execute("INSERT INTO a_stock_basic (code, name) SELECT code, name FROM df")
    n = conn.execute("SELECT COUNT(*) FROM a_stock_basic").fetchone()[0]
    conn.close()
    return int(n)
