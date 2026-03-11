"""历史日K线：单只标的写入 a_stock_daily，前复权。"""
from __future__ import annotations

def update_daily_kline(code: str, start_date: str | None = None, end_date: str | None = None) -> int:
    """
    code: 6位代码如 000001，或 000001.SZ。
    start_date/end_date: YYYYMMDD，默认最近一年。
    """
    try:
        import akshare as ak
        import pandas as pd
    except ImportError:
        return 0
    from datetime import datetime, timedelta
    from ..storage.duckdb_manager import get_conn, ensure_tables

    code = str(code).strip().split(".")[0]
    if not code or len(code) < 5:
        return 0
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")

    # 优先东方财富接口（含北交所）
    df = None
    if getattr(ak, "stock_zh_a_hist_em", None):
        try:
            df = ak.stock_zh_a_hist_em(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        except Exception:
            pass
    if df is None or df.empty:
        try:
            df = ak.stock_zh_a_hist(symbol=code, start_date=start_date, end_date=end_date, period="daily", adjust="qfq")
        except Exception:
            return 0
    if df is None or df.empty:
        return 0

    # 列名：日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额
    col_date = "日期"
    if col_date not in df.columns:
        return 0
    df = df.copy()
    df["code"] = code
    df = df.rename(columns={
        "开盘": "open", "收盘": "close", "最高": "high", "最低": "low",
        "成交量": "volume", "成交额": "amount",
    })
    cols = ["code", "date", "open", "high", "low", "close", "volume", "amount"]
    df["date"] = pd.to_datetime(df[col_date]).dt.date
    df = df[["code", "date", "open", "high", "low", "close", "volume", "amount"]]

    conn = get_conn()
    ensure_tables(conn)
    conn.register("tmp", df)
    conn.execute("""
        INSERT INTO a_stock_daily (code, date, open, high, low, close, volume, amount)
        SELECT code, date, open, high, low, close, volume, amount FROM tmp
        ON CONFLICT (code, date) DO UPDATE SET
        open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close,
        volume=EXCLUDED.volume, amount=EXCLUDED.amount
    """)
    n = len(df)
    conn.close()
    return int(n)
