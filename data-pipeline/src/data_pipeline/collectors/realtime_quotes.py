"""实时行情快照：全市场，写入 a_stock_realtime。建议每30秒更新。"""
from __future__ import annotations

import datetime

def update_realtime_quotes() -> int:
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from ..storage.duckdb_manager import get_conn, ensure_tables

    df = ak.stock_zh_a_spot_em()
    if df is None or df.empty:
        return 0
    now = datetime.datetime.now()
    # 东方财富列名：代码, 名称, 最新价, 涨跌幅, 成交量, 成交额 等
    cols_map = {"代码": "code", "名称": "name", "最新价": "latest_price", "涨跌幅": "change_pct", "成交量": "volume", "成交额": "amount"}
    rename = {k: v for k, v in cols_map.items() if k in df.columns}
    df = df.rename(columns=rename)
    df["snapshot_time"] = now
    for cn, alt in [("volume", "成交量"), ("amount", "成交额"), ("latest_price", "最新价"), ("change_pct", "涨跌幅")]:
        if cn not in df.columns and alt in df.columns:
            df[cn] = df[alt]
    need = ["code", "name", "latest_price", "change_pct", "volume", "amount", "snapshot_time"]
    out = df[[c for c in need if c in df.columns]].copy()
    for c in need:
        if c not in out.columns:
            out[c] = 0.0 if c != "name" else ""
    out = out[need].fillna(0)

    conn = get_conn()
    ensure_tables(conn)
    conn.register("tmp", out)
    conn.execute("""
        INSERT INTO a_stock_realtime (code, name, latest_price, change_pct, volume, amount, snapshot_time)
        SELECT code, name, latest_price, change_pct, volume, amount, snapshot_time FROM tmp
    """)
    n = len(out)
    conn.close()
    return n
