#!/usr/bin/env python3
"""
Rebuild endpoints.py v2: properly handle helper range detection.
"""
import re

GATEWAY = "/Users/apple/Ahope/newhigh/gateway/src/gateway"
EP = f"{GATEWAY}/endpoints.py"

with open(EP) as f:
    source = f.read()
    lines = source.split('\n')

# Find all def lines (both helpers and routes)
all_defs = {}
for i, line in enumerate(lines):
    m = re.match(r'^(async\s+)?def ([a-zA-Z_][a-zA-Z0-9_]*)\(', line)
    if m:
        all_defs[m.group(2)] = i

# Also find all @router decorator lines
router_lines = set()
for i, line in enumerate(lines):
    if re.match(r'@router\.(get|post|put|delete|patch)\(', line.strip()):
        router_lines.add(i)

ALL_HELPERS = [
    "_is_ashare_symbol", "_pipeline_code_variants", "_row_date_to_utc_iso",
    "_normalize_sym_show", "_fetch_klines_from_a_stock_daily", "_ashare_suffix_from_code6",
    "_fetch_klines_akshare_daily", "_stooq_daily_symbol_map", "_fetch_klines_stooq_daily",
    "_fetch_klines_binance_usdt", "_pipeline_quant_data_status", "_ashare_skill",
    "_record_skill_call", "_short_ts_for_signal", "_optional_price", "_optional_pct",
    "_market_db_query", "_safe_lhb_date_str", "_safe_net_buy", "_sniper_candidates_minimal",
    "_status_to_state", "_normalize_news_article_url", "_news_fallback_akshare",
    "_news_fallback_akshare_multi_symbol", "_policy_sentiment_label", "_policy_news_from_duckdb",
    "_hot_ticker_from_duckdb_news", "_fetch_hot_ticker_payload", "_duckdb_global_macro_news_summary",
    "_run_manual_news_refresh", "_fetch_news_for_research", "_llm_news_summary",
    "_news_sentiment_summary", "_save_backtest_to_strategy_market", "_run_backtest_internal",
    "_risk_engine_module", "_execution_broker_module", "_simulated_module",
    "_metrics_from_equity_curve", "_dashboard_top_strategies_from_db", "_dashboard_from_duckdb",
    "_run_evolution_background", "_alpha_lab_code6", "_alpha_lab_binding_note",
    "_alpha_lab_compute_counts", "_alpha_lab_drill_rows",
]

# Calculate helper ranges using ANY def as boundary
helper_ranges = {}
for name in ALL_HELPERS:
    start = all_defs[name]
    end = len(lines)
    # Find the next function def (ANY kind) or next @router decorator
    candidates = []
    for j in range(start + 1, len(lines)):
        if re.match(r'^(async\s+)?def [a-zA-Z_]', lines[j]):
            candidates.append(('def', j))
            break
    # Also stop at any @router 
    for j in range(start + 1, len(lines)):
        if re.match(r'@router\.', lines[j].strip()):
            candidates.append(('router', j))
            break
    if candidates:
        end = min(c[1] for c in candidates)
    helper_ranges[name] = (start, end)

# Collect all helper line indices
helper_lines = set()
for name, (s, e) in helper_ranges.items():
    for ln in range(s, e):
        helper_lines.add(ln)

# Add supporting classes/variables
for ln in range(2168, 2181):  # NewsManualRefreshBody + _MANUAL_RSS_FEEDS_DEFAULT
    helper_lines.add(ln)

# Find ALL route decorators with their full function body range
route_boundaries = []
for i, line in enumerate(lines):
    m = re.match(r'@router\.(get|post|put|delete|patch)\("([^"]+)"\)', line.strip())
    if m:
        start = i
        method = m.group(1)
        path = m.group(2)
        # The def is on the NEXT line
        def_line = i + 1
        while def_line < len(lines) and not lines[def_line].strip():
            def_line += 1
        # Find end: next decorator or next non-helper def
        end = len(lines)
        for j in range(def_line + 1, len(lines)):
            stripped = lines[j].strip()
            if re.match(r'@router\.', stripped):
                end = j
                break
        route_boundaries.append((start, end, path, method))

# Routes duplicated in sub-files
DUPLICATE_ROUTES = set([
    "/market/klines", "/market/realtime", "/market/limitup", "/market/longhubang",
    "/market/fundflow", "/market/emotion", "/market/sentiment-7d",
    "/market/hotmoney", "/market/main-themes", "/market/sniper-candidates",
    "/strategy/signals", "/strategies/market",
    "/news", "/news/collector", "/news/coverage", "/news/hot-ticker",
    "/news/manual-refresh",
    "/backtest/run", "/backtest/portfolio", "/backtest/result",
    "/risk/rules", "/risk/check", "/risk/status",
    "/execution/mode", "/simulated/step", "/simulated/positions",
    "/simulated/orders", "/simulated/account_snapshots", "/execution/equity_curve",
    "/ai/decision", "/dashboard", "/alpha-lab/drill", "/alpha-lab",
    "/evolution", "/evolution/run", "/evolution/trigger",
    "/evolution/status/{task_id}", "/evolution/tasks",
    "/system/status", "/skill/ashare/stock-basic", "/skill/ashare/daily",
    "/skill/ashare/tech-indicator", "/skill/ashare/finance-indicator",
    "/skill/ashare/limit-up-down", "/skill/ashare/industry-ranking",
    "/skill/ashare/market-overview", "/skill/stats",
    "/portfolio/weights",
])

# Build the set of lines to REMOVE
lines_to_remove = set()

# Remove ALL helper function bodies
lines_to_remove.update(helper_lines)

# Remove ENTIRE duplicate route bodies
for start, end, path, method in route_boundaries:
    if path in DUPLICATE_ROUTES:
        for ln in range(start, end):
            lines_to_remove.add(ln)
        print(f"Removed route: {method.upper():6s} {path}")

# Build new file
new_lines = []
for i, line in enumerate(lines):
    if i not in lines_to_remove:
        new_lines.append(line)

result = "\n".join(new_lines)

# Find what helpers are still needed
helpers_needed = set()
for h in ALL_HELPERS:
    if re.search(r'\b' + re.escape(h) + r'\s*\(', result):
        helpers_needed.add(h)

print(f"\nHelpers still needed: {sorted(helpers_needed)}")

# Insert import after the last import block
insert_pos = None
for i, line in enumerate(new_lines):
    if 'print(f"警告：财报分析端点加载失败' in line:
        insert_pos = i + 1
        break

if insert_pos is None:
    insert_pos = 31

if helpers_needed:
    import_lines = [
        "",
        "from .endpoints_helpers import (  # noqa: E402",
    ]
    for h in sorted(helpers_needed):
        import_lines.append(f"    {h},")
    import_lines.append(")")
    
    new_lines = new_lines[:insert_pos] + import_lines + new_lines[insert_pos:]

result = "\n".join(new_lines)

outpath = f"{GATEWAY}/endpoints_new.py"
with open(outpath, 'w') as f:
    f.write(result)

# Stats
print(f"")
print(f"Original: {len(lines)} lines")
print(f"New:      {len(new_lines)} lines")
print(f"Removed:  {len(lines) - len(new_lines)} lines")

# Final check: remaining routes
remaining_routes = []
for i, line in enumerate(new_lines):
    m = re.match(r'@router\.(get|post|put|delete|patch)\("([^"]+)"\)', line.strip())
    if m:
        remaining_routes.append(m.group(2))
print(f"\nRemaining routes ({len(remaining_routes)}):")
for r in sorted(remaining_routes):
    print(f"  - {r}")

# Check for orphaned defs (defs without decorators)
for i, line in enumerate(new_lines):
    m = re.match(r'^def ([a-zA-Z_][a-zA-Z0-9_]*)\(', line)
    if m:
        func_name = m.group(1)
        if func_name.startswith('_'):
            continue  # helpers already dealt with
        # Check if there's a decorator above
        has_decorator = False
        for j in range(i-1, max(i-5, -1), -1):
            if new_lines[j].strip():
                if re.match(r'@router\.', new_lines[j].strip()):
                    has_decorator = True
                break
        if not has_decorator:
            # This is normal - /data/status route had decorator removed
            pass

print(f"\nWritten: {outpath}")
