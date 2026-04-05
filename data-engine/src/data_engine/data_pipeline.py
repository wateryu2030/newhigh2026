"""Data pipeline: fetch from Binance / Yahoo / akshare / Tushare -> normalize -> store in ClickHouse."""

import datetime as dt
from typing import List

from .connector_binance import fetch_klines
from .connector_akshare import fetch_klines_akshare
from .connector_tushare import fetch_ohlcv
from .clickhouse_storage import get_client, ensure_tables, insert_ohlcv


def run_pipeline(
    symbol: str,
    interval: str,
    limit: int = 500,
    clickhouse_host: str = "localhost",
    clickhouse_port: int = 9000,
) -> int:
    """
    Fetch klines from Binance and write to ClickHouse.
    Returns number of rows written.
    """
    rows = fetch_klines(symbol=symbol, interval=interval, limit=limit)
    if not rows:
        return 0

    client = get_client(host=clickhouse_host, port=clickhouse_port)
    ensure_tables(client)
    insert_ohlcv(client, rows, interval)
    return len(rows)


def run_pipeline_batch(
    symbols: List[str],
    intervals: List[str],
    limit_per_symbol: int = 500,
    clickhouse_host: str = "localhost",
    clickhouse_port: int = 9000,
) -> int:
    """Run pipeline for multiple symbols and intervals. Returns total rows written."""
    client = get_client(host=clickhouse_host, port=clickhouse_port)
    ensure_tables(client)
    total = 0
    for symbol in symbols:
        for interval in intervals:
            rows = fetch_klines(symbol=symbol, interval=interval, limit=limit_per_symbol)
            if rows:
                insert_ohlcv(client, rows, interval)
                total += len(rows)
    return total


def run_pipeline_ashare(
    symbols: List[str],
    start_date: str | None = None,
    end_date: str | None = None,
    period: str = "daily",
    adjust: str = "qfq",
    clickhouse_host: str = "localhost",
    clickhouse_port: int = 9000,
) -> int:
    """
    拉取 A 股数据（akshare）并写入 ClickHouse。
    symbols: 6 位代码列表，如 ["000001", "600519"]
    start_date/end_date: "20240101"，默认最近 1 年
    period: "daily" | "weekly" | "monthly"
    """
    if not end_date:
        end_d = dt.datetime.now(dt.timezone.utc)
        end_date = end_d.strftime("%Y%m%d")
    if not start_date:
        start_date = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=365)).strftime("%Y%m%d")
    interval = "1d" if period == "daily" else "1w" if period == "weekly" else "1M"
    client = get_client(host=clickhouse_host, port=clickhouse_port)
    ensure_tables(client)
    total = 0
    for symbol in symbols:
        rows = fetch_klines_akshare(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            period=period,
            adjust=adjust,
        )
        if rows:
            insert_ohlcv(client, rows, interval)
            total += len(rows)
    return total


def run_pipeline_tushare(
    symbols: List[str],
    start_date: str | None = None,
    end_date: str | None = None,
    period: str = "daily",
    adjust: str = "",
    clickhouse_host: str = "localhost",
    clickhouse_port: int = 9000,
) -> int:
    """
    拉取 A 股数据（Tushare）并写入 ClickHouse。
    symbols: 6 位代码列表，如 ["000001", "600519"]
    start_date/end_date: "20240101"，默认最近 30 天
    period: "daily" | "weekly" | "monthly"
    adjust: 复权类型，"qfq"（前复权）、"hfq"（后复权）、""（不复权）
    """
    if not end_date:
        end_d = dt.datetime.now(dt.timezone.utc)
        end_date = end_d.strftime("%Y%m%d")
    if not start_date:
        start_date = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=30)).strftime("%Y%m%d")

    interval = "1d" if period == "daily" else "1w" if period == "weekly" else "1M"
    client = get_client(host=clickhouse_host, port=clickhouse_port)
    ensure_tables(client)
    total = 0

    for symbol in symbols:
        try:
            rows = fetch_ohlcv(
                code=symbol,
                start_date=start_date,
                end_date=end_date,
                period=period,
                adjust=adjust,
            )
            if rows:
                insert_ohlcv(client, rows, interval)
                total += len(rows)
                print(f"✓ 成功获取 {symbol} 数据: {len(rows)} 条")
            else:
                print(f"⚠ 未获取到 {symbol} 数据")
        except Exception as e:  # pylint: disable=broad-exception-caught  # Continue processing other symbols on error
            print(f"✗ 获取 {symbol} 数据失败: {e}")

    return total
