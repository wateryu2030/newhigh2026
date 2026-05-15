#!/usr/bin/env python3
"""Extract shared helper functions from endpoints.py into endpoints_helpers.py
and then strip the duplicates + routes from endpoints.py"""

import re
import sys
from pathlib import Path

GATEWAY = Path("/Users/apple/Ahope/newhigh/gateway/src/gateway")
EP = GATEWAY / "endpoints.py"

SOURCE = EP.read_text("utf-8")

lines = SOURCE.split("\n")

# --- Step 1: collect ALL helper function line ranges (the def _* lines) ---
helper_starts = {}
for i, line in enumerate(lines):
    m = re.match(r'^(async\s+)?def (_[a-z_0-9]+)\(', line)
    if m:
        helper_starts[m.group(2)] = i

# All helpers needed by sub-files (44 total)
ALL_HELPERS = [
    "_is_ashare_symbol",
    "_pipeline_code_variants",
    "_row_date_to_utc_iso",
    "_normalize_sym_show",
    "_fetch_klines_from_a_stock_daily",
    "_ashare_suffix_from_code6",
    "_fetch_klines_akshare_daily",
    "_stooq_daily_symbol_map",
    "_fetch_klines_stooq_daily",
    "_fetch_klines_binance_usdt",
    "_pipeline_quant_data_status",
    "_ashare_skill",
    "_record_skill_call",
    "_short_ts_for_signal",
    "_optional_price",
    "_optional_pct",
    "_market_db_query",
    "_safe_lhb_date_str",
    "_safe_net_buy",
    "_sniper_candidates_minimal",
    "_status_to_state",
    "_normalize_news_article_url",
    "_news_fallback_akshare",
    "_news_fallback_akshare_multi_symbol",
    "_policy_sentiment_label",
    "_policy_news_from_duckdb",
    "_hot_ticker_from_duckdb_news",
    "_fetch_hot_ticker_payload",
    "_duckdb_global_macro_news_summary",
    "_run_manual_news_refresh",
    "_fetch_news_for_research",
    "_llm_news_summary",
    "_news_sentiment_summary",
    "_save_backtest_to_strategy_market",
    "_run_backtest_internal",
    "_risk_engine_module",
    "_execution_broker_module",
    "_simulated_module",
    "_metrics_from_equity_curve",
    "_dashboard_top_strategies_from_db",
    "_dashboard_from_duckdb",
    "_run_evolution_background",
    "_alpha_lab_code6",
    "_alpha_lab_binding_note",
    "_alpha_lab_compute_counts",
    "_alpha_lab_drill_rows",
]

# Check that all helpers exist
missing = [h for h in ALL_HELPERS if h not in helper_starts]
if missing:
    print(f"ERROR: helpers not found: {missing}", file=sys.stderr)
    sys.exit(1)

# --- Step 2: extract function bodies ---
# Build a dict of {name: (start_line, end_line_exclusive)}
helper_ranges = {}
for name in ALL_HELPERS:
    start = helper_starts[name]
    # Find the next def at same indentation level, or end of file
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r'^(async\s+)?def [_a-z]', lines[j]):
            end = j
            break
    helper_ranges[name] = (start, end)

# Also capture the supporting classes/variables needed
# NewsManualRefreshBody (line 2169-2173)
# _MANUAL_RSS_FEEDS_DEFAULT (line 2176-2181)

print(f"Found {len(helper_ranges)} helper function ranges")
for name, (s, e) in sorted(helper_ranges.items()):
    print(f"  {name}: lines {s+1}-{e}")

# --- Step 3: Build the helpers file content ---
HELPERS_IMPORT = '''"""Shared helper functions extracted from endpoints.py to break circular imports.

These helpers are used by the 7 sub-module files (endpoints_market.py, endpoints_news.py,
endpoints_strategy.py, endpoints_system.py, endpoints_execution.py, endpoints_frontend.py,
endpoints_skills.py) to avoid circular imports with endpoints.py.

Usage:
    from .endpoints_helpers import <helper_name>
"""

import asyncio
import json
import logging
import os
from typing import Any, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel, Field

from core.ashare_symbol import normalize_ashare_symbol

from .response_utils import json_fail, json_ok

_log = logging.getLogger(__name__)


# --- Supporting classes & constants ---


class NewsManualRefreshBody(BaseModel):
    """手动拉取 RSS 宏观入库并可选推送一条汇总到 NEWS_BREAKING_WEBHOOK_URL（飞书等）。"""
    send_webhook: bool = False


# 首页「新闻手刷」专用：少量源 + 较短超时，避免反代/浏览器在完整默认 RSS 列表上超时或 500
_MANUAL_RSS_FEEDS_DEFAULT = (
    "http://feeds.bbci.co.uk/news/world/rss.xml,"
    "http://feeds.bbci.co.uk/news/business/rss.xml,"
    "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml"
)


'''

# Extract each helper body
for name in ALL_HELPERS:
    start, end = helper_ranges[name]
    body = "\n".join(lines[start:end])
    HELPERS_IMPORT += body + "\n\n"

EP_HELPERS_PATH = GATEWAY / "endpoints_helpers.py"
EP_HELPERS_PATH.write_text(HELPERS_IMPORT, "utf-8")
print(f"\nWritten: {EP_HELPERS_PATH} ({len(HELPERS_IMPORT)} chars)")

# --- Step 4: Verify no syntax errors ---
import py_compile
try:
    py_compile.compile(str(EP_HELPERS_PATH), doraise=True)
    print("Syntax check: OK")
except py_compile.PyCompileError as e:
    print(f"Syntax error: {e}", file=sys.stderr)
    sys.exit(1)

print("\nDone! Now update sub-files and endpoints.py")
