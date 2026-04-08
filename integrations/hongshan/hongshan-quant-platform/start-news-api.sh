#!/bin/bash
# 政策新闻 FastAPI（默认 8001）：DuckDB news_items（与 Gateway 同 QUANT_SYSTEM_DUCKDB_PATH）
set -e
HS="$(cd "$(dirname "$0")/.." && pwd)"
NEWHIGH="$(cd "$HS/../.." && pwd)"
POLICY="$HS/policy-news"
export PYTHONPATH="${NEWHIGH}/data-pipeline/src:${POLICY}${PYTHONPATH:+:$PYTHONPATH}"
python3 "$POLICY/news_database.py" init
exec python3 "$POLICY/news_database.py" api
