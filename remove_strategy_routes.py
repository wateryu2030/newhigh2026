#!/usr/bin/env python3
"""Remove STRATEGY routes from endpoints.py."""
import re

with open('gateway/src/gateway/endpoints.py') as f:
    lines = f.readlines()

# Strategy route ranges (0-indexed)
# /strategy/signals 825-892, /strategies 1618-1627, /strategies/market 1640-1715
# /backtest/run 1787-1854, /backtest/portfolio 1857-1906, /backtest/result 1909-1942
# /portfolio/weights 1945-1948, /risk/status 1951-1958, /risk/rules 1978-1993
# /risk/rules POST 1996-2009, /risk/check 2012-2027

# IMPORTANT: Keep these shared helper functions:
# _short_ts_for_signal (lines 722-735 in current file)
# _optional_price (lines 736-747)
# _optional_pct (lines 748-756)
# _market_db_query (lines 757-777)
# But those are outside the ranges below, so we're safe.

remove = set()
ranges = [
    (824, 892),    # /strategy/signals
    (1617, 1627),  # /strategies
    (1639, 1715),  # /strategies/market
    (1786, 1854),  # /backtest/run
    (1856, 1906),  # /backtest/portfolio
    (1908, 1942),  # /backtest/result
    (1944, 1948),  # /portfolio/weights
    (1950, 1958),  # /risk/status
    (1977, 1993),  # /risk/rules GET
    (1995, 2009),  # /risk/rules POST
    (2011, 2027),  # /risk/check
]
for s, e in ranges:
    for i in range(s, e + 1):
        remove.add(i)

new_lines = [line for i, line in enumerate(lines) if i not in remove]
with open('gateway/src/gateway/endpoints.py', 'w') as f:
    f.writelines(new_lines)

removed = len(lines) - len(new_lines)
print(f"Removed {removed} lines (strategy routes)")
