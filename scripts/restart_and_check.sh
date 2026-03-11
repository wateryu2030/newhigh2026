#!/usr/bin/env bash
# Restart gateway (and optionally frontend), then run OpenClaw design-goal check.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "========== Stopping existing services =========="
for port in 8000 3000; do
  PID=$(lsof -ti ":$port" 2>/dev/null || true)
  if [ -n "$PID" ]; then
    echo "Killing process on port $port (PID $PID)"
    kill -9 $PID 2>/dev/null || true
    sleep 1
  fi
done

echo "========== Starting gateway (:8000) =========="
source .venv/bin/activate 2>/dev/null || true
uvicorn gateway.app:app --host 127.0.0.1 --port 8000 &
GWPID=$!
sleep 2
if ! kill -0 $GWPID 2>/dev/null; then
  echo "Gateway failed to start."
  exit 1
fi
echo "Gateway started (PID $GWPID)."

echo "========== Waiting for /health =========="
for i in 1 2 3 4 5; do
  if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health | grep -q 200; then
    echo "Gateway healthy."
    break
  fi
  [ $i -eq 5 ] && echo "Gateway not ready." && exit 1
  sleep 1
done

echo "========== OpenClaw design-goal check =========="
bash scripts/openclaw_check_design.sh
CHECK_RESULT=$?

echo ""
echo "Gateway is running at http://127.0.0.1:8000 (PID $GWPID)"
echo "Start frontend: cd frontend && npm run dev  → http://localhost:3000"
[ $CHECK_RESULT -ne 0 ] && exit $CHECK_RESULT
exit 0
