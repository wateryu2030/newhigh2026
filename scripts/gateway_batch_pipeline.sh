#!/usr/bin/env bash
# Gateway 与 DuckDB 批处理互斥管线：停 Gateway → 写入市场快照 → 启 Gateway → 新鲜度探针。
# 中期演进：将长耗时采集迁到独立 Worker + 队列（如 Redis），Gateway 进程仅只读 DuckDB，可消除写锁与停服窗口。
# 用法（仓库根）：
#   bash scripts/gateway_batch_pipeline.sh
#   bash scripts/gateway_batch_pipeline.sh --skip-realtime   # 涨停/资金流仍跑
#   bash scripts/gateway_batch_pipeline.sh --no-smoke        # 不写库后仍起 Gateway，不跑探针
#   PIPELINE_SKIP_START_GATEWAY=1 bash scripts/gateway_batch_pipeline.sh   # 仅停+采集（调试）
# 环境：需 .venv；可选根目录 .env（QUANT_SYSTEM_DUCKDB_PATH 等）。
# DuckDB：若停掉 8000 后仍报锁冲突，多半是 Jupyter / 其它 Python 进程占库；本脚本在采集前会等待解锁，
# 或设 PIPELINE_KILL_DUCKDB_HOLDERS=1 强杀占用该文件的进程（慎用）。
# 端口占用：EADDRINUSE 时执行 lsof -iTCP:8000 -sTCP:LISTEN 与 lsof -iTCP:3000 -sTCP:LISTEN 后处理。
set -euo pipefail

PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p "$ROOT/logs"

load_root_env() {
  if [[ -f "$ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$ROOT/.env" || true
    set +a
  fi
}

load_root_env

PY="${ROOT}/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  echo "[pipeline] 错误: 未找到 $PY" >&2
  exit 2
fi

export PYTHONPATH="${ROOT}/gateway/src:${ROOT}/data-pipeline/src:${ROOT}/core/src:${ROOT}/data-engine/src:${ROOT}/execution-engine/src:${ROOT}/backtest-engine/src:${ROOT}/risk-engine/src:${ROOT}/strategy/src:${ROOT}/openclaw_engine:${ROOT}/data/src:${ROOT}:${ROOT}/lib"

NO_SMOKE=0
REFRESH_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-realtime) REFRESH_ARGS+=(--skip-realtime); shift ;;
    --skip-limitup) REFRESH_ARGS+=(--skip-limitup); shift ;;
    --skip-fundflow) REFRESH_ARGS+=(--skip-fundflow); shift ;;
    --no-smoke) NO_SMOKE=1; shift ;;
    -h|--help)
      grep '^#' "$0" | head -n 12 | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "[pipeline] 未知参数: $1" >&2
      exit 2
      ;;
  esac
done

kill_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    local pids
    pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
    if [[ -n "${pids:-}" ]]; then
      echo "[pipeline] 释放端口 ${port}，PID: ${pids}"
      # shellcheck disable=SC2086
      kill -9 ${pids} 2>/dev/null || true
    fi
  fi
}

stop_gateway() {
  echo "[pipeline] 停止 Gateway（避免 DuckDB 写锁冲突）…"
  kill_port 8000
  pkill -f "uvicorn gateway.app" 2>/dev/null || true
  pkill -f "uvicorn.*gateway\.app:app" 2>/dev/null || true
  sleep 1
}

# 与 duckdb_manager 默认一致：环境变量优先，否则仓库 data/quant_system.duckdb
_duckdb_file() {
  local p="${QUANT_SYSTEM_DUCKDB_PATH:-}"
  [[ -z "$p" ]] && p="${QUANT_DB_PATH:-}"
  [[ -z "$p" ]] && p="${NEWHIGH_MARKET_DUCKDB_PATH:-}"
  [[ -z "$p" ]] && p="$ROOT/data/quant_system.duckdb"
  echo "$p"
}

# 停 Gateway 后仍可能有其它 Python（Notebook、脚本）持有 DuckDB 写锁，需等其释放或强杀
wait_duckdb_unlock_or_fail() {
  local db
  db="$(_duckdb_file)"
  [[ -f "$db" ]] || { echo "[pipeline] DuckDB 文件不存在，跳过锁等待: $db"; return 0; }
  local max="${PIPELINE_DUCKDB_WAIT_ATTEMPTS:-45}"
  local sleep_s="${PIPELINE_DUCKDB_WAIT_SEC:-2}"
  local i
  for ((i = 1; i <= max; i++)); do
    local holders
    holders=""
    if command -v lsof >/dev/null 2>&1; then
      holders=$(lsof "$db" 2>/dev/null | awk 'NR>1 {print $2}' | sort -u | tr '\n' ' ' | sed 's/[[:space:]]*$//')
    fi
    if [[ -z "${holders// }" ]]; then
      [[ "$i" -gt 1 ]] && echo "[pipeline] DuckDB 已无进程占用，继续采集"
      return 0
    fi
    echo "[pipeline] DuckDB 仍被占用 ($i/$max): PID ${holders}" >&2
    echo "[pipeline] 提示: 关闭 Jupyter/正在跑采集的终端，或执行: lsof \"$db\"" >&2
    if [[ "${PIPELINE_KILL_DUCKDB_HOLDERS:-0}" == "1" ]]; then
      echo "[pipeline] PIPELINE_KILL_DUCKDB_HOLDERS=1 → 结束占用进程…" >&2
      # shellcheck disable=SC2086
      kill -9 ${holders} 2>/dev/null || true
      sleep 2
      continue
    fi
    sleep "$sleep_s"
  done
  echo "[pipeline] 错误: 超时仍无法独占 DuckDB: $db" >&2
  return 1
}

start_gateway() {
  local UV="${ROOT}/.venv/bin/uvicorn"
  [[ -x "$UV" ]] || UV="uvicorn"
  echo "[pipeline] 启动 Gateway http://127.0.0.1:8000 …"
  nohup "$UV" gateway.app:app --host 127.0.0.1 --port 8000 --reload \
    >>"$ROOT/logs/gateway.out" 2>&1 &
  echo $! >"$ROOT/logs/gateway.pid"
  echo "[pipeline] Gateway PID $(cat "$ROOT/logs/gateway.pid")"
  for i in $(seq 1 60); do
    if curl -sf --max-time 2 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
      echo "[pipeline] Gateway 就绪（${i}s）"
      return 0
    fi
    sleep 0.5
  done
  echo "[pipeline] 警告: Gateway /health 未及时就绪，请查 logs/gateway.out" >&2
  return 1
}

INGEST_RC=0
stop_gateway
if ! wait_duckdb_unlock_or_fail; then
  echo "[pipeline] 可重试: PIPELINE_KILL_DUCKDB_HOLDERS=1 bash $0 …（会 kill 占用该库的 PID）" >&2
  if [[ "${PIPELINE_SKIP_START_GATEWAY:-0}" != "1" ]]; then
    start_gateway || true
  fi
  exit 1
fi

echo "[pipeline] 执行市场快照写入…"
# bash + set -u：部分 Bash（含部分 5.x）对空数组的 "${REFRESH_ARGS[@]}" 仍报 unbound variable，显式分支最稳
if [[ ${#REFRESH_ARGS[@]} -eq 0 ]]; then
  REFRESH_OK=0
  "$PY" "$ROOT/scripts/refresh_terminal_market_snapshots.py" || REFRESH_OK=$?
else
  REFRESH_OK=0
  "$PY" "$ROOT/scripts/refresh_terminal_market_snapshots.py" "${REFRESH_ARGS[@]}" || REFRESH_OK=$?
fi
if [[ "$REFRESH_OK" -ne 0 ]]; then
  INGEST_RC=1
  echo "[pipeline] 采集阶段失败 (exit $INGEST_RC)，仍将尝试拉起 Gateway" >&2
fi

if [[ "${PIPELINE_SKIP_START_GATEWAY:-0}" == "1" ]]; then
  echo "[pipeline] PIPELINE_SKIP_START_GATEWAY=1，跳过启动 Gateway"
  exit "$INGEST_RC"
fi

start_gateway || true

SMOKE_RC=0
if [[ "$NO_SMOKE" == "1" ]]; then
  echo "[pipeline] --no-smoke，跳过新鲜度探针"
else
  # 入库后重启有间隔：默认允许现货快照 25 分钟内算新鲜（东财全市场抓取耗时可观）
  MAX_RT="${PIPELINE_MAX_AGE_REALTIME_SEC:-1500}"
  MAX_LU="${PIPELINE_MAX_AGE_LIMITUP_SEC:-7200}"
  echo "[pipeline] 新鲜度探针 (realtime<=${MAX_RT}s limitup<=${MAX_LU}s)…"
  if ! "$PY" "$ROOT/scripts/check_data_freshness.py" \
    --base-url "${GATEWAY_BASE_URL:-http://127.0.0.1:8000}" \
    --max-age-realtime "$MAX_RT" \
    --max-age-limitup "$MAX_LU" \
    --require-realtime; then
    SMOKE_RC=1
    echo "[pipeline] 新鲜度探针失败" >&2
  fi
fi

if [[ "$INGEST_RC" -ne 0 ]]; then
  exit "$INGEST_RC"
fi
exit "$SMOKE_RC"
