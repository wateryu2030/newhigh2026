#!/usr/bin/env python3
"""Remove MARKET routes from endpoints.py (lines 359-443, 617-631, 634-669, 672-689, 928-947, 950-1011, 1052-1127, 1130-1193, 1196-1252, 1255-1282, 1355-1387, 1390-1421, 1463-1621)."""
import re

with open('gateway/src/gateway/endpoints.py') as f:
    lines = f.readlines()

# Collect all lines to remove (0-indexed)
remove = set()
ranges = [
    (359, 443), (617, 631), (634, 669), (672, 689),
    (928, 947), (950, 1011), (1052, 1127), (1130, 1193),
    (1196, 1252), (1255, 1282), (1355, 1387), (1390, 1421),
    (1463, 1621),
]
for s, e in ranges:
    for i in range(s, e + 1):
        remove.add(i)

new_lines = [line for i, line in enumerate(lines) if i not in remove]
with open('gateway/src/gateway/endpoints.py', 'w') as f:
    f.writelines(new_lines)

removed = len(lines) - len(new_lines)
print(f"Removed {removed} lines (market routes)")
