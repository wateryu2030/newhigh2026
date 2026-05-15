#!/usr/bin/env python3
"""List all routes in endpoints.py"""
import re

with open('/Users/apple/Ahope/newhigh/gateway/src/gateway/endpoints.py') as f:
    lines = f.readlines()

routes = []
for i, line in enumerate(lines):
    m = re.match(r'@router\.(get|post|put|delete|patch)\("([^"]+)"\)', line.strip())
    if m:
        routes.append((i+1, m.group(1), m.group(2), lines[i+1].strip() if i+1 < len(lines) else ''))

print(f'Total routes in endpoints.py: {len(routes)}')
for lineno, method, path, next_line in routes:
    print(f'  {lineno}: {method.upper():6s} {path:40s} {next_line}')
