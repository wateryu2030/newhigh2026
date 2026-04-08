"""ClickHouse storage for OHLCV. Tables: market_1m, market_5m, market_1h, market_1d."""

import datetime as dt
from typing import List

from clickhouse_driver import Client

from core import OHLCV, INTERVAL_TO_TABLE


def get_client(host: str = "localhost", port: int = 9000, database: str = "default") -> Client:
    """Create ClickHouse client."""
    return Client(host=host, port=port, database=database)


def ensure_tables(client: Client) -> None:
    """Create market_* tables if they do not exist."""
    for table in ("market_1m", "market_5m", "market_1h", "market_1d"):
        client.execute(f"""
            CREATE TABLE IF NOT EXISTS {table} (
                symbol String,
                timestamp DateTime64(3),
                open Float64,
                high Float64,
                low Float64,
                close Float64,
                volume Float64,
                interval String
            ) ENGINE = MergeTree()
            ORDER BY (symbol, timestamp)
            """)


def insert_ohlcv(client: Client, rows: List[OHLCV], interval: str) -> None:
    """Insert OHLCV rows into the appropriate table."""
    table = INTERVAL_TO_TABLE.get(interval)
    if not table:
        raise ValueError(f"Unknown interval: {interval}")

    data = [
        (
            r.symbol,
            r.timestamp,
            r.open,
            r.high,
            r.low,
            r.close,
            r.volume,
            r.interval,
        )
        for r in rows
    ]
    client.execute(
        f"""
        INSERT INTO {table} (symbol, timestamp, open, high, low, close, volume, interval)
        VALUES
        """,
        data,
    )


def query_ohlcv(  # pylint: disable=too-many-positional-arguments
    client: Client,
    symbol: str,
    interval: str,
    start: dt.datetime | None = None,
    end: dt.datetime | None = None,
    limit: int = 10000,
) -> List[OHLCV]:
    """Query OHLCV from storage."""
    table = INTERVAL_TO_TABLE.get(interval)
    if not table:
        raise ValueError(f"Unknown interval: {interval}")

    where = ["symbol = %(symbol)s"]
    params = {"symbol": symbol, "limit": limit}
    if start is not None:
        where.append("timestamp >= %(start)s")
        params["start"] = start
    if end is not None:
        where.append("timestamp <= %(end)s")
        params["end"] = end

    q = f"""
        SELECT symbol, timestamp, open, high, low, close, volume, interval
        FROM {table}
        WHERE {' AND '.join(where)}
        ORDER BY timestamp
        LIMIT %(limit)s
    """
    result = client.execute(q, params)
    return [
        OHLCV(
            symbol=row[0],
            timestamp=row[1],
            open=row[2],
            high=row[3],
            low=row[4],
            close=row[5],
            volume=row[6],
            interval=row[7],
        )
        for row in result
    ]
