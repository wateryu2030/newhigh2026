#!/usr/bin/env python3
"""Remove SYSTEM routes from endpoints.py."""
import re

with open('gateway/src/gateway/endpoints.py') as f:
    lines = f.readlines()

# System route ranges (0-indexed)
# /data/status 409-463, /data/daily-coverage 466-530, /data/sources 539-547
# /data/ensure-stocks 550-562, /data/incremental 679-719
# /system/status 939-1024, /system/health-detail 1027-1035, /health/detailed 1038-1046
# /system/backtest-errors 1049-1079, /data/quality 1655-1700, /audit/logs 1703-1725

remove = set()
ranges = [
    (408, 463),    # /data/status
    (465, 530),    # /data/daily-coverage
    (538, 547),    # /data/sources
    (549, 562),    # /data/ensure-stocks
    (678, 719),    # /data/incremental
    (938, 1024),   # /system/status
    (1026, 1035),  # /system/health-detail
    (1037, 1046),  # /health/detailed
    (1048, 1079),  # /system/backtest-errors
    (1654, 1700),  # /data/quality
    (1702, 1725),  # /audit/logs
]
for s, e in ranges:
    for i in range(s, e + 1):
        remove.add(i)

# Keep _pipeline_quant_data_status (362-406) and _status_to_state (940-946) - verify they're not in remove set
# These were found at:
# _pipeline_quant_data_status: line 362 (0-indexed: 361) ... verify
# _status_to_state: line 940 (0-indexed: 939)

new_lines = [line for i, line in enumerate(lines) if i not in remove]
with open('gateway/src/gateway/endpoints.py', 'w') as f:
    f.writelines(new_lines)

removed = len(lines) - len(new_lines)
print(f"Removed {removed} lines (system routes)")
