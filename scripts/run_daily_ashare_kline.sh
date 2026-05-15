#!/usr/bin/env bash
# 自动化：东财日 K 增量/回补（写入 quant_system.duckdb → a_stock_daily）。
# 建议 cron / launchd 每日收盘后执行，例如 18:10。
#
# 环境变量（可选）：
#   DAILY_ASHARE_CODES_LIMIT  默认 800（与调度器「短窗口」配合；全市场可设 5000+）
#   ASHARE_NO_PROXY          设为 0 则去掉本脚本的 --no-proxy（默认带 --no-proxy，避免坏代理）
#   ASHARE_ON_EMPTY_TRY_TUSHARE  设为 1 且已配置 TUSHARE_TOKEN 时，东财某批 0 行则该批改走 Tushare
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ -f ".venv/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source ".venv/bin/activate"
fi
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
LIMIT="${DAILY_ASHARE_CODES_LIMIT:-800}"
NO_PROXY=(--no-proxy)
if [[ "${ASHARE_NO_PROXY:-1}" == "0" ]]; then
  NO_PROXY=()
fi
exec "$PY" scripts/backfill_a_stock_daily.py "${NO_PROXY[@]}" --codes-limit "$LIMIT" "$@"
