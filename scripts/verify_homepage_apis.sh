#!/usr/bin/env bash
# Verify（可重复）：首页 Dashboard 依赖的 Gateway 路径是否 200。
# 用法: GATEWAY_BASE_URL=http://127.0.0.1:8000 bash scripts/verify_homepage_apis.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${GATEWAY_BASE_URL:-http://127.0.0.1:8000}"
BASE="${BASE%/}"
echo "Gateway: $BASE"
fail=0
check() {
  local path="$1"
  local ms="${2:-25}"
  code=$(curl -sS -o /tmp/vh_$$.json -w "%{http_code}" --max-time "$ms" "${BASE}${path}" || echo "000")
  if [[ "$code" != "200" ]]; then
    echo "FAIL $path -> HTTP $code"
    fail=1
  else
    echo "OK   $path -> HTTP $code"
  fi
}
check "/health" 10
check "/api/dashboard" 30
check "/api/data/status" 25
check "/api/market/emotion" 25
check "/api/system/data-overview" 45
# health-detail 为信封 { ok, data }
code=$(curl -sS -o /tmp/vh_hd_$$.json -w "%{http_code}" --max-time 25 "${BASE}/api/system/health-detail" || echo "000")
if [[ "$code" != "200" ]]; then
  echo "FAIL /api/system/health-detail -> HTTP $code"
  fail=1
else
  echo "OK   /api/system/health-detail -> HTTP $code"
fi
rm -f /tmp/vh_$$.json /tmp/vh_hd_$$.json 2>/dev/null || true
exit "$fail"
