#!/usr/bin/env bash
# 停调度 → 跑 1 次 a_stock_daily 回补 → 后台再起 start_schedulers monitor
#
# 用法（仓库根）：
#   bash scripts/stop_scheduler_backfill_restart.sh
#   DAILY_ASHARE_CODES_LIMIT=500 bash scripts/stop_scheduler_backfill_restart.sh
#   # 使用 Tushare 渠道（.env 已配 TUSHARE_TOKEN）：
#   BACKFILL_SOURCE=tushare_daily DAILY_ASHARE_CODES_LIMIT=500 bash scripts/stop_scheduler_backfill_restart.sh
#
# 若仍报 DuckDB 锁：先释放其它写库进程（如占用 8000 的 Gateway 若其长期持锁），或：
#   lsof /path/to/data/quant_system.duckdb
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="python3"
fi
LOGDIR="$ROOT/logs/scheduler"
mkdir -p "$LOGDIR"
LIMIT="${DAILY_ASHARE_CODES_LIMIT:-300}"
SRC="${BACKFILL_SOURCE:-ashare_daily_kline}"

echo "[1/3] 停止 start_schedulers.py monitor …"
# 仅匹配 monitor，避免误伤其它 python
if pgrep -f "${ROOT}/scripts/start_schedulers.py monitor" >/dev/null 2>&1; then
  pkill -TERM -f "${ROOT}/scripts/start_schedulers.py monitor" 2>/dev/null || true
else
  pkill -TERM -f "start_schedulers.py monitor" 2>/dev/null || true
fi
sleep 2
if pgrep -f "start_schedulers.py monitor" >/dev/null 2>&1; then
  echo "  仍在运行，发送 KILL …"
  pkill -KILL -f "start_schedulers.py monitor" 2>/dev/null || true
  sleep 1
fi

DB="$ROOT/data/quant_system.duckdb"
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if lsof "$DB" 2>/dev/null | grep -q .; then
    echo "  等待 DuckDB 文件锁释放 …"
    sleep 2
  else
    break
  fi
done

echo "[2/3] 日线回补（source=${SRC}, codes_limit=${LIMIT}）…"
if [[ "$SRC" == "tushare_daily" ]]; then
  "$PY" scripts/backfill_a_stock_daily.py --source tushare_daily --codes-limit "$LIMIT"
else
  "$PY" scripts/backfill_a_stock_daily.py --no-proxy --codes-limit "$LIMIT"
fi

echo "[3/3] 后台启动调度 monitor …"
nohup "$PY" "$ROOT/scripts/start_schedulers.py" monitor >>"$LOGDIR/monitor.log" 2>&1 &
echo "  已启动 PID $!"
echo "  日志: $LOGDIR/monitor.log"
echo "  查看: tail -f $LOGDIR/monitor.log"
