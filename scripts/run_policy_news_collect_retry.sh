#!/usr/bin/env bash
# Auto-fixed by Cursor on 2026-04-03: 政策采集前探活 gov.cn，失败则等待重试，减轻 08:30 DNS 瞬断导致整批跳过。
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="$ROOT/scripts/run_policy_news_collect.sh"
MAX_ATTEMPTS="${POLICY_COLLECT_DNS_RETRIES:-3}"
SLEEP_SEC="${POLICY_COLLECT_RETRY_SLEEP_SEC:-120}"
PROBE_URL="${POLICY_COLLECT_PROBE_URL:-https://www.gov.cn}"

attempt=1
while [[ "$attempt" -le "$MAX_ATTEMPTS" ]]; do
  if curl -sf --max-time 20 "$PROBE_URL" -o /dev/null; then
    exec "$RUN" "$@"
  fi
  echo "[policy-collect-retry] attempt $attempt/$MAX_ATTEMPTS: probe $PROBE_URL failed, sleep ${SLEEP_SEC}s" >&2
  if [[ "$attempt" -ge "$MAX_ATTEMPTS" ]]; then
    break
  fi
  sleep "$SLEEP_SEC"
  attempt=$((attempt + 1))
done

echo "[policy-collect-retry] probe still failing after $MAX_ATTEMPTS attempts; running collector anyway (may fail fast)" >&2
exec "$RUN" "$@"
