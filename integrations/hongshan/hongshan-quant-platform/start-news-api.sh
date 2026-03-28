#!/bin/bash
# 政策新闻 FastAPI（默认 8001），依赖 integrations/hongshan/policy-news/news_database.py
set -e
HS="$(cd "$(dirname "$0")/.." && pwd)"
POLICY="$HS/policy-news"
export PYTHONPATH="${POLICY}${PYTHONPATH:+:$PYTHONPATH}"
python3 "$POLICY/news_database.py" init
exec python3 "$POLICY/news_database.py" api
