#!/usr/bin/env bash
# 自动化：复制 A 股 DuckDB → 初始化扩展表 → 跑进化循环（含特征落库）
# 可选：单独补特征时加 --features-only
#
# 用法（在 newhigh 仓库根目录）:
#   bash scripts/run_openclaw_data_and_evolution.sh
#   bash scripts/run_openclaw_data_and_evolution.sh --features-only   # 只跑特征计算落库
#   bash scripts/run_openclaw_data_and_evolution.sh --no-copy         # 跳过复制（已有 data/quant.duckdb）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 使用项目 venv（若有）
if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

PYTHON="${PYTHON:-python3}"
if ! command -v "$PYTHON" &>/dev/null; then
  PYTHON=python
fi

# 确保 duckdb 已安装（复制与 init 脚本依赖）
echo "[1/4] Ensuring duckdb is installed..."
"$PYTHON" -m pip install -q duckdb

RUN_COPY=true
RUN_FEATURES_ONLY=false
for x in "$@"; do
  case "$x" in
    --no-copy)       RUN_COPY=false ;;
    --features-only) RUN_FEATURES_ONLY=true ;;
  esac
done

if [ "$RUN_FEATURES_ONLY" = true ]; then
  echo "[*] Running only: compute_features_to_duckdb.py (optional: --symbols 600519,000001 --limit 500 --max-symbols 200)"
  "$PYTHON" scripts/compute_features_to_duckdb.py
  exit $?
fi

# 1) 复制 A 股数据到 newhigh 本地 DuckDB
if [ "$RUN_COPY" = true ]; then
  echo "[2/4] Copying A-share DuckDB (astock -> newhigh)..."
  if ! "$PYTHON" scripts/copy_astock_duckdb_to_newhigh.py; then
    echo "Warning: copy failed (e.g. source astock DB missing). Continuing."
  fi
else
  echo "[2/4] Skipping copy (--no-copy)."
fi

# 2) 初始化扩展表 features_daily / backtest_runs
echo "[3/4] Initializing DuckDB extensions (features_daily, backtest_runs)..."
if ! "$PYTHON" scripts/init_newhigh_duckdb_extensions.py; then
  echo "Warning: init failed (e.g. data/quant.duckdb not found). Continuing."
fi

# 3) 跑进化循环（内含数据补全 + 特征计算落库 + 策略/回测）
echo "[4/4] Running OpenClaw evolution cycle..."
EVO_ARGS=()
for x in "$@"; do
  case "$x" in
    --no-copy) ;;
    *) EVO_ARGS+=("$x") ;;
  esac
done
"$PYTHON" scripts/openclaw_evolution_cycle.py "${EVO_ARGS[@]}"
echo "Done."
