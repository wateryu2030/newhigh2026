#!/usr/bin/env bash
# 停止占用 8000/3000 的进程并后台重启 Gateway + Next 前端。
# 用法：
#   bash scripts/restart_gateway_frontend.sh                    # 开发：next dev
#   NEWHIGH_FRONTEND_PROD=1 bash scripts/restart_gateway_frontend.sh   # 部署：next build + next start
set -euo pipefail

# 优先使用 Homebrew / 系统 Node，避免 PATH 里 ~/.local/bin/npm 指向已失效的 node（会导致 Next 起不来、3000 拒绝连接）
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/logs"

kill_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [ -n "${pids:-}" ]; then
      echo "[restart] 释放端口 ${port}，PID: ${pids}"
      # shellcheck disable=SC2086
      kill -9 ${pids} 2>/dev/null || true
    else
      echo "[restart] 端口 ${port} 无监听"
    fi
  else
    echo "[restart] 未找到 lsof，跳过按端口杀进程"
  fi
}

echo "[restart] 停止旧进程（uvicorn / next）…"
kill_port 8000
kill_port 3000
pkill -f "uvicorn gateway.app" 2>/dev/null || true
pkill -f "uvicorn.*gateway" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next start" 2>/dev/null || true
sleep 1

# 与 Gateway 启动所需 import 路径一致（按需可再扩充）
export PYTHONPATH="${ROOT}/gateway/src:${ROOT}/data-pipeline/src:${ROOT}/core/src:${ROOT}/data-engine/src:${ROOT}/execution-engine/src:${ROOT}/backtest-engine/src:${ROOT}/risk-engine/src:${ROOT}/strategy/src:${ROOT}/openclaw_engine:${ROOT}/data/src:${ROOT}:${ROOT}/lib"

UV="${ROOT}/.venv/bin/uvicorn"
if [ ! -x "$UV" ]; then
  UV="uvicorn"
fi

echo "[restart] 启动 Gateway http://127.0.0.1:8000 …"
nohup "$UV" gateway.app:app --host 127.0.0.1 --port 8000 --reload \
  >>"$ROOT/logs/gateway.out" 2>&1 &
echo $! >"$ROOT/logs/gateway.pid"
echo "[restart] Gateway PID $(cat "$ROOT/logs/gateway.pid")，日志 $ROOT/logs/gateway.out"

cd "$ROOT/frontend"
if ! command -v npm >/dev/null 2>&1 || ! npm --version >/dev/null 2>&1; then
  echo "[restart] 错误: 未找到可用的 npm/node，请安装 Node 或修复 PATH（建议: brew install node）" >&2
  exit 1
fi
if [ "${NEWHIGH_FRONTEND_PROD:-}" = "1" ]; then
  echo "[restart] 前端生产模式：npm run build …"
  npm run build >>"$ROOT/logs/frontend.out" 2>&1
  echo "[restart] 启动前端 next start http://0.0.0.0:3000 …"
  nohup npm run start >>"$ROOT/logs/frontend.out" 2>&1 &
else
  echo "[restart] 启动前端 next dev http://127.0.0.1:3000 …"
  nohup npm run dev >>"$ROOT/logs/frontend.out" 2>&1 &
fi
echo $! >"$ROOT/logs/frontend.pid"
cd "$ROOT"
echo "[restart] 前端 PID $(cat "$ROOT/logs/frontend.pid")，日志 $ROOT/logs/frontend.out"
echo "[restart] 完成。"
echo "[restart] 检查: curl -s -o /dev/null -w 'Gateway: %{http_code}\\n' http://127.0.0.1:8000/health"
echo "[restart]       curl -s -o /dev/null -w 'Next: %{http_code}\\n' http://127.0.0.1:3000/"
