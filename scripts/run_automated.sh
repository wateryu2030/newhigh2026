#!/usr/bin/env bash
# 自动化执行入口：加载 .env、Tushare 拉取、全周期（扫描→AI→信号）。可被 cron/launchd 调用。
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs
LOG="$ROOT/logs/automated.log"
PYTHON="${ROOT}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG"
"$PYTHON" "$ROOT/scripts/run_automated.py" "$@" >> "$LOG" 2>&1 || true
echo "----- end -----" >> "$LOG"
