#!/usr/bin/env bash
# Auto-fixed by Cursor on 2026-04-03: 供 cron/launchd 使用，统一走 .venv + .env + PYTHONPATH。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}/data-pipeline/src:${PYTHONPATH:-}"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
PY="$ROOT/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "[policy-collect] ERROR: missing $PY — create venv: python3 -m venv .venv && pip install -r requirements.txt requests beautifulsoup4" >&2
  exit 1
fi
exec "$PY" "$ROOT/integrations/hongshan/policy-news/news_collector.py" "$@"
