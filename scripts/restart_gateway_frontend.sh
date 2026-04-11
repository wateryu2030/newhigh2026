#!/usr/bin/env bash
# 停止占用 8000/3000 的进程并后台重启 Gateway + Next 前端。
# 用法：
#   bash scripts/restart_gateway_frontend.sh                    # 开发：next dev（默认先删 .next，避免 HMR chunk 错配）
#   NEWHIGH_NEXT_SKIP_NEXT_CLEAN=1 bash scripts/restart_gateway_frontend.sh  # 保留 .next 加快重启（再出现 ./NNN.js 勿用）
#   NEWHIGH_FRONTEND_PROD=1 bash scripts/restart_gateway_frontend.sh   # 部署：next build + standalone node server.js
set -euo pipefail

# 优先使用 Homebrew / 系统 Node，避免 PATH 里 ~/.local/bin/npm 指向已失效的 node（会导致 Next 起不来、3000 拒绝连接）
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/logs"

# 先注入环境变量再启 Gateway/Next：与 dotenv 一致，且保证 uvicorn 子进程继承 API_PROXY_TARGET、CORS_ORIGINS 等
load_root_env() {
  if [[ -f "$ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env" || true
    set +a
  fi
  export API_PROXY_TARGET="${API_PROXY_TARGET:-http://127.0.0.1:8000}"
}

load_root_env

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
export PYTHONPATH="${ROOT}/gateway/src:${ROOT}/ai-models/src:${ROOT}/data-pipeline/src:${ROOT}/core/src:${ROOT}/data-engine/src:${ROOT}/execution-engine/src:${ROOT}/backtest-engine/src:${ROOT}/risk-engine/src:${ROOT}/strategy/src:${ROOT}/openclaw_engine:${ROOT}/data/src:${ROOT}:${ROOT}/lib"

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
  echo "[restart] 同步 static/public → .next/standalone（next.config output=standalone 必需）…"
  mkdir -p .next/standalone/.next
  rm -rf .next/standalone/.next/static
  cp -R .next/static .next/standalone/.next/static
  if [ -d public ]; then
    rm -rf .next/standalone/public
    cp -R public .next/standalone/public
  fi
  echo "[restart] 启动 Next standalone server.js http://0.0.0.0:3000（API_PROXY_TARGET=$API_PROXY_TARGET）…"
  cd .next/standalone
  nohup env HOSTNAME=0.0.0.0 PORT=3000 API_PROXY_TARGET="$API_PROXY_TARGET" node server.js >>"$ROOT/logs/frontend.out" 2>&1 &
  echo $! >"$ROOT/logs/frontend.pid"
else
  # 默认删 .next：HMR 后常见 Cannot find module './NNN.js'。跳过清缓存用 NEWHIGH_NEXT_SKIP_NEXT_CLEAN=1
  if [[ "${NEWHIGH_NEXT_SKIP_NEXT_CLEAN:-}" != "1" ]]; then
    echo "[restart] 清理前端 .next（开发模式，避免陈旧 webpack chunk）…"
    rm -rf .next
  elif [[ -d .next && ! -f .next/server/middleware-manifest.json ]]; then
    echo "[restart] 缺 middleware-manifest，清理 .next …"
    rm -rf .next
  fi
  mkdir -p .next/server
  # Next 14 dev 冷启动首包编译前可能 require 此文件；占位防 500，随后由 dev 覆盖
  if [[ ! -f .next/server/middleware-manifest.json ]]; then
    printf '%s\n' '{"version":3,"middleware":{},"functions":{},"sortedMiddleware":[]}' >.next/server/middleware-manifest.json
  fi
  echo "[restart] 启动前端 next dev http://127.0.0.1:3000 …"
  nohup npm run dev >>"$ROOT/logs/frontend.out" 2>&1 &
  echo $! >"$ROOT/logs/frontend.pid"
  # Next dev 启动阶段会删掉预置的 middleware-manifest；短暂补写，直至 Next 自行生成
  (
    MW_STUB='{"version":3,"middleware":{},"functions":{},"sortedMiddleware":[]}'
    for _ in $(seq 1 120); do
      mkdir -p "$ROOT/frontend/.next/server"
      if [[ ! -f "$ROOT/frontend/.next/server/middleware-manifest.json" ]]; then
        printf '%s\n' "$MW_STUB" >"$ROOT/frontend/.next/server/middleware-manifest.json"
      fi
      sleep 0.25
    done
  ) &
  # 等待 / 与 /api/* 首编译完成，降低 Cannot find module './NNN.js' 竞态
  echo "[restart] 等待 Next 编译就绪（首页 + /api 反代）…"
  for i in $(seq 1 120); do
    if curl -sf -o /dev/null "http://127.0.0.1:3000/" 2>/dev/null; then
      code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:3000/api/news?limit=1" 2>/dev/null || echo 000)
      if [[ "$code" == "200" ]]; then
        echo "[restart] Next 就绪（约 ${i}s）"
        break
      fi
    fi
    sleep 1
  done
fi
cd "$ROOT"
echo "[restart] 前端 PID $(cat "$ROOT/logs/frontend.pid")，日志 $ROOT/logs/frontend.out"
echo "[restart] 完成。"
echo "[restart] 检查: curl -s -o /dev/null -w 'Gateway: %{http_code}\\n' http://127.0.0.1:8000/health"
echo "[restart]       curl -s -o /dev/null -w 'Next: %{http_code}\\n' http://127.0.0.1:3000/"
echo "[restart]       curl -s -o /dev/null -w 'Next /api/news: %{http_code}\\n' 'http://127.0.0.1:3000/api/news?limit=1'"
