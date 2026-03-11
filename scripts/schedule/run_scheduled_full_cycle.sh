#!/bin/bash
# 定时任务实际执行的脚本：在 newhigh 根目录下用 venv 跑 run_full_cycle.py，日志写入 logs/。
# 由 launchd 在锁屏/后台时按计划调用；也可手动执行测试。
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
mkdir -p logs
LOG="$ROOT/logs/full_cycle.log"
PYTHON="${ROOT}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi
echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG"
"$PYTHON" "$ROOT/scripts/run_full_cycle.py" "$@" >> "$LOG" 2>&1 || true
echo "----- end -----" >> "$LOG"
