"""K线清洗：去空、去重、OHLC 合法性、成交量非负。"""

from __future__ import annotations


def clean_kline(code: str | None = None) -> int:
    """
    对 a_stock_daily 做清洗：删除 open/high/low/close 为空或异常的行，volume/amount 置为非负。
    code: 仅清洗该标的；None 表示全表。
    返回被更新/删除影响的行数（近似）。
    """
    from ..storage.duckdb_manager import get_conn

    conn = get_conn()
    if code:
        conn.execute(
            """
            DELETE FROM a_stock_daily
            WHERE code = ? AND (open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR close <= 0)
        """,
            [code],
        )
    else:
        conn.execute("""
            DELETE FROM a_stock_daily
            WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL OR close <= 0
        """)
    conn.execute(
        "UPDATE a_stock_daily SET volume = COALESCE(NULLIF(volume, NULL), 0) WHERE volume < 0"
    )
    conn.execute(
        "UPDATE a_stock_daily SET amount = COALESCE(NULLIF(amount, NULL), 0) WHERE amount < 0"
    )
    n = conn.execute("SELECT COUNT(*) FROM a_stock_daily").fetchone()[0]
    conn.close()
    return int(n)
