"""Shared constants."""
# Table names for market data (ClickHouse)
TABLE_1M = "market_1m"
TABLE_5M = "market_5m"
TABLE_1H = "market_1h"
TABLE_1D = "market_1d"

INTERVALS = ("1m", "5m", "1h", "1d")
INTERVAL_TO_TABLE = {
    "1m": TABLE_1M,
    "5m": TABLE_5M,
    "1h": TABLE_1H,
    "1d": TABLE_1D,
}
