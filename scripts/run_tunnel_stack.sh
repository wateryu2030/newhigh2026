#!/usr/bin/env bash
# 供 LaunchAgent 常驻：Gateway :8000 + Next :3000（与 Cloudflare Tunnel → http://127.0.0.1:3000 配套）
# 任一进程退出则结束脚本，launchd 的 KeepAlive 会整体重启。
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/logs"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export PYTHONPATH="$ROOT"

# 加载 .env（与 Gateway 一致）
if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi

# shellcheck source=/dev/null
source "$ROOT/.venv/bin/activate"

echo "[$(date -Iseconds)] tunnel stack starting" >> "$ROOT/logs/tunnel_stack.log"

uvicorn gateway.app:app --host 127.0.0.1 --port 8000 >> "$ROOT/logs/gateway_boot.log" 2>&1 &
GWPID=$!

for _ in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
    break
  fi
  sleep 1
done

cd "$ROOT/frontend"
export API_PROXY_TARGET="${API_PROXY_TARGET:-http://127.0.0.1:8000}"
# output: 'standalone' 时应用 `start:standalone`（复制 .next/static + public 再 node server.js），
# 避免 `next start` 与 standalone 产物不一致导致公网 /_next/static 404。
if [ "${NEWHIGH_FORCE_FRONTEND_REBUILD:-}" = "1" ]; then
  echo "[$(date -Iseconds)] NEWHIGH_FORCE_FRONTEND_REBUILD=1 → rm .next" >> "$ROOT/logs/tunnel_stack.log"
  rm -rf .next
fi
if [ ! -f .next/BUILD_ID ]; then
  echo "[$(date -Iseconds)] building frontend (missing .next/BUILD_ID)..." >> "$ROOT/logs/tunnel_stack.log"
  npm run build >> "$ROOT/logs/frontend_build_boot.log" 2>&1
fi

npm run start:standalone >> "$ROOT/logs/next_boot.log" 2>&1 &
NWPID=$!

echo "[$(date -Iseconds)] gw=$GWPID next=$NWPID" >> "$ROOT/logs/tunnel_stack.log"

while kill -0 "$GWPID" 2>/dev/null && kill -0 "$NWPID" 2>/dev/null; do
  sleep 15
done

echo "[$(date -Iseconds)] one process died, restarting stack" >> "$ROOT/logs/tunnel_stack.log"
kill "$GWPID" 2>/dev/null || true
kill "$NWPID" 2>/dev/null || true
wait "$GWPID" 2>/dev/null || true
wait "$NWPID" 2>/dev/null || true
sleep 2
exit 1
