#!/usr/bin/env bash
# 一键：结束本机 newhigh 相关进程 → 可选全量 npm ci → 前端 clean build → standalone 启动
# → 后台启动 Gateway。用于修复公网 /_next/static 404/500、chunk 错配等。
#
# 用法（在项目根）：
#   bash scripts/full_rebuild_restart.sh
#   FULL_NPM_CI=1 bash scripts/full_rebuild_restart.sh   # 顺带 rm -rf node_modules && npm ci（更慢）
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"

mkdir -p "$ROOT/logs"
LOG="$ROOT/logs/full_rebuild_restart.log"
exec >>"$LOG" 2>&1
echo "[$(date -Iseconds)] full_rebuild_restart start"

# 加载 .env（API_PROXY_TARGET 等）
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi
export API_PROXY_TARGET="${API_PROXY_TARGET:-http://127.0.0.1:8000}"

# ---------- 结束进程 ----------
echo "[step] kill listeners :3000 :8000"
for port in 3000 8000; do
  pids=$(lsof -ti "tcp:$port" 2>/dev/null || true)
  if [[ -n "${pids:-}" ]]; then
    # shellcheck disable=SC2086
    kill -9 ${pids} 2>/dev/null || true
  fi
done
pkill -f "uvicorn gateway.app" 2>/dev/null || true
pkill -f "uvicorn.*gateway" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next start" 2>/dev/null || true
pkill -f "standalone/server.js" 2>/dev/null || true

DB="$ROOT/data/quant_system.duckdb"
if [[ -f "$DB" ]]; then
  for pid in $(lsof -t "$DB" 2>/dev/null || true); do
    echo "[step] kill duckdb holder PID $pid"
    kill -9 "$pid" 2>/dev/null || true
  done
fi
sleep 2

# ---------- Python 路径（与 restart 脚本一致）----------
export PYTHONPATH="${ROOT}/gateway/src:${ROOT}/ai-models/src:${ROOT}/data-pipeline/src:${ROOT}/core/src:${ROOT}/data-engine/src:${ROOT}/execution-engine/src:${ROOT}/backtest-engine/src:${ROOT}/risk-engine/src:${ROOT}/strategy/src:${ROOT}/openclaw_engine:${ROOT}/data/src:${ROOT}:${ROOT}/lib"

# ---------- Gateway ----------
UV="${ROOT}/.venv/bin/uvicorn"
[[ -x "$UV" ]] || UV="uvicorn"
echo "[step] start gateway :8000"
nohup "$UV" gateway.app:app --host 127.0.0.1 --port 8000 --reload >>"$ROOT/logs/gateway.out" 2>&1 &
echo $! >"$ROOT/logs/gateway.pid"
for _ in $(seq 1 90); do
  if curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
    echo "[step] gateway ok"
    break
  fi
  sleep 1
done

# ---------- 前端：清理构建缓存 ----------
cd "$ROOT/frontend"
# 安装依赖时切勿 export NODE_ENV=production，否则 npm 跳过 devDependencies → 缺 tailwindcss/postcss → next build 失败
unset NODE_ENV || true

if [[ "${FULL_NPM_CI:-}" = "1" ]]; then
  echo "[step] FULL_NPM_CI=1 → rm node_modules && npm ci"
  rm -rf node_modules
  npm ci
else
  echo "[step] npm ci（与 package-lock 一致，含 devDependencies）"
  npm ci
fi

echo "[step] rm -rf .next && npm run build"
rm -rf .next
npm run build

echo "[step] npm run start:standalone（cwd 将在脚本内切到 .next/standalone）"
export NODE_ENV=production
nohup npm run start:standalone >>"$ROOT/logs/frontend.out" 2>&1 &
echo $! >"$ROOT/logs/frontend.pid"

for _ in $(seq 1 120); do
  if curl -sf "http://127.0.0.1:3000/" >/dev/null || curl -sf "http://localhost:3000/" >/dev/null; then
    echo "[step] next ok"
    break
  fi
  sleep 1
done

sleep 3
VERIFY_URL="http://127.0.0.1:3000"
curl -sf "$VERIFY_URL/" >/dev/null || VERIFY_URL="http://localhost:3000"
if bash "$ROOT/scripts/verify_next_static_local.sh" "$VERIFY_URL"; then
  echo "[$(date -Iseconds)] full_rebuild_restart DONE OK"
else
  echo "[$(date -Iseconds)] full_rebuild_restart verify FAILED (see logs)" >&2
  exit 1
fi
