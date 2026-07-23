#!/usr/bin/env python3
"""快速批量采集器 - 避免 DuckDB 锁竞争"""
from __future__ import annotations
import os, sys, time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "src"))

for k in ['HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy']:
    os.environ.pop(k, None)

import duckdb
from data_pipeline.storage.duckdb_manager import get_db_path, ensure_tables

DB = get_db_path()

def batch_kline_update(codes: list[str]) -> int:
    """批量更新K线，只开一次写连接"""
    from datetime import datetime, timedelta

    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

    conn = duckdb.connect(DB)  # read/write
    ensure_tables(conn)
    total = 0

    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0

    for i, code in enumerate(codes):
        code = str(code).strip().split(".", maxsplit=1)[0]
        if not code or len(code) < 5:
            continue
        try:
            df = ak.stock_zh_a_hist_em(
                symbol=code, period="daily",
                start_date=start_date, end_date=end_date, adjust="qfq"
            )
        except Exception:
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code, period="daily",
                    start_date=start_date, end_date=end_date, adjust="qfq"
                )
            except Exception:
                continue

        if df is None or df.empty:
            continue
        col_date = "日期"
        if col_date not in df.columns:
            continue
        df = df.copy()
        df["code"] = code
        df = df.rename(columns={
            "开盘": "open", "收盘": "close", "最高": "high",
            "最低": "low", "成交量": "volume", "成交额": "amount"
        })
        df["date"] = pd.to_datetime(df[col_date]).dt.date
        df = df[["code", "date", "open", "high", "low", "close", "volume", "amount"]]

        conn.register("_tmp", df)
        conn.execute("""
            INSERT INTO a_stock_daily (code, date, open, high, low, close, volume, amount)
            SELECT code, date, open, high, low, close, volume, amount FROM _tmp
            ON CONFLICT (code, date) DO UPDATE SET
            open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low,
            close=EXCLUDED.close, volume=EXCLUDED.volume, amount=EXCLUDED.amount
        """)
        conn.unregister("_tmp")
        n = len(df)
        total += n
        if (i + 1) % 5 == 0:
            print(f"  [{i+1}/{len(codes)}] {code}: +{n}行 (累计{total})")
        time.sleep(0.1)

    conn.close()
    return total


def batch_fundflow() -> int:
    """资金流批量"""
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0

    conn = duckdb.connect(DB)
    ensure_tables(conn)
    now = __import__('datetime').datetime.now()

    df = ak.stock_individual_fund_flow_rank(indicator="今日")
    if df is None or df.empty:
        conn.close()
        return 0

    df = df.copy()
    df["snapshot_time"] = now
    df["snapshot_date"] = now.date()
    for src, dst in [("代码", "code"), ("名称", "name")]:
        if src in df.columns:
            df = df.rename(columns={src: dst})
    mc = [c for c in df.columns if "主力" in str(c) or "净流入" in str(c)]
    if mc:
        df = df.rename(columns={mc[0]: "main_net_inflow"})
    if "main_net_inflow" not in df.columns:
        df["main_net_inflow"] = 0.0
    # Clean non-numeric values like "-"
    df["main_net_inflow"] = pd.to_numeric(df["main_net_inflow"], errors="coerce").fillna(0.0)

    cols = ["code", "name", "main_net_inflow", "snapshot_date", "snapshot_time"]
    out = df[[c for c in cols if c in df.columns]]

    conn.register("_tmp", out)
    conn.execute("INSERT INTO a_stock_fundflow (code, name, main_net_inflow, snapshot_date, snapshot_time) SELECT code, name, main_net_inflow, snapshot_date, snapshot_time FROM _tmp")
    n = len(out)
    conn.close()
    return n


def batch_limitup() -> int:
    """涨停池"""
    try:
        import akshare as ak
    except ImportError:
        return 0

    conn = duckdb.connect(DB)
    ensure_tables(conn)
    now = __import__('datetime').datetime.now()

    df = ak.stock_zt_pool_em(date=now.strftime("%Y%m%d"))
    if df is None or df.empty:
        conn.close()
        return 0

    df = df.copy()
    df["snapshot_time"] = now
    for src, dst in [("代码", "code"), ("名称", "name"), ("最新价", "price"),
                       ("涨跌幅", "change_pct"), ("连板数", "limit_up_times")]:
        if src in df.columns:
            df = df.rename(columns={src: dst})

    for c in ["price", "change_pct", "limit_up_times"]:
        if c not in df.columns:
            df[c] = 0.0
    out = df[["code", "name", "price", "change_pct", "limit_up_times", "snapshot_time"]].fillna(0)

    conn.register("_tmp", out)
    conn.execute("INSERT INTO a_stock_limitup (code, name, price, change_pct, limit_up_times, snapshot_time) SELECT code, name, price, change_pct, limit_up_times, snapshot_time FROM _tmp")
    n = len(out)
    conn.close()
    return n


def main():
    import datetime

    codes = [
        "600519","000858","601398","600036","000001","600276","000333",
        "601318","600900","002415","600030","601012","000725","600809",
        "601166","600585","000651","300750","601888","002594",
        "600488","600370","000890","002007","000538","002791",
        "600673","600741","002236","600160"
    ]

    print(f"[{datetime.datetime.now():%H:%M:%S}] 快速批量采集启动")
    print(f"  数据库: {DB} ({os.path.getsize(DB)//1024//1024}MB)")

    t0 = time.time()
    n_kline = batch_kline_update(codes)
    print(f"  [1/3] K线: +{n_kline}行 ({time.time()-t0:.1f}s)")

    t0 = time.time()
    n_ff = batch_fundflow()
    print(f"  [2/3] 资金流: +{n_ff}行 ({time.time()-t0:.1f}s)")

    t0 = time.time()
    n_lu = batch_limitup()
    print(f"  [3/3] 涨停: +{n_lu}行 ({time.time()-t0:.1f}s)")

    # 验证
    c = duckdb.connect(DB, read_only=True)
    kl = c.execute('SELECT COUNT(*) FROM a_stock_daily').fetchone()[0]
    ff = c.execute('SELECT COUNT(*) FROM a_stock_fundflow').fetchone()[0]
    lu = c.execute('SELECT COUNT(*) FROM a_stock_limitup').fetchone()[0]
    c.close()
    print(f"  完成: K线{kl}行 | 资金流{ff}行 | 涨停{lu}行")


if __name__ == "__main__":
    main()
