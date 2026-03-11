#!/usr/bin/env bash
# 启动 Gateway，等待就绪后执行目标检查。
# 用法: bash scripts/start_services.sh
# 可选: API_BASE=http://127.0.0.1:8000 bash scripts/start_services.sh
# 仅检查（不启动）: python scripts/check_goals.py
# 前端单独启动: cd frontend && npm run dev
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

PORT="${PORT:-8000}"
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
export API_BASE
PIDFILE="$ROOT/scripts/.gateway.pid"

# 若已在运行则只做检查
if [ -f "$PIDFILE" ]; then
  OLD_PID=$(cat "$PIDFILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Gateway already running (PID $OLD_PID), running checks only."
    python scripts/check_goals.py
    exit $?
  fi
  rm -f "$PIDFILE"
fi

echo "Starting Gateway on port $PORT..."
uvicorn gateway.app:app --host 0.0.0.0 --port "$PORT" &
GWPID=$!
echo $GWPID > "$PIDFILE"

# 等待健康
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s -o /dev/null -w "%{http_code}" "$API_BASE/health" 2>/dev/null | grep -q 200; then
    echo "Gateway ready (PID $GWPID)."
    break
  fi
  if [ "$i" -eq 10 ]; then
    echo "Gateway did not become ready."
    kill $GWPID 2>/dev/null; rm -f "$PIDFILE"
    exit 1
  fi
  sleep 1
done

echo "Running goal checks (live server)..."
export API_BASE
USE_LIVE=1 python scripts/check_goals.py
EXIT=$?
echo ""
echo "Gateway is running at $API_BASE (PID $GWPID). Stop with: kill $GWPID"
exit $EXIT
