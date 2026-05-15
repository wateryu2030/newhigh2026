#!/usr/bin/env python3
"""Remove NEWS routes from endpoints.py."""
import re

with open('gateway/src/gateway/endpoints.py') as f:
    lines = f.readlines()

# News route ranges (0-indexed)
# /news 1227-1271, /news/collector 1333-1354, /news/coverage 1357-1379
# /news/hot-ticker 1479-1496, /news/manual-refresh 1604-1629
# /news/web-insight 1632-1731, /research/news-summary 1843-1893
remove = set()
ranges = [
    (1226, 1271), (1332, 1354), (1356, 1379),
    (1478, 1496), (1603, 1629), (1631, 1731),
    (1842, 1893),
]
for s, e in ranges:
    for i in range(s, e + 1):
        remove.add(i)

new_lines = [line for i, line in enumerate(lines) if i not in remove]
with open('gateway/src/gateway/endpoints.py', 'w') as f:
    f.writelines(new_lines)

removed = len(lines) - len(new_lines)
print(f"Removed {removed} lines (news routes)")
