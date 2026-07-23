#!/usr/bin/env bash
# newhigh 数据增量包 — 每日定时全量采集
# 由 launchd 触发，每天 20:00 后自动执行
# 日志：logs/data-packages-collect.log
#
# 执行顺序：
# 1. 财务报告采集（前300只蓝筹，日增 — 增量插入不去重已有）
# 2. 公司传闻采集（雪球+news_items回溯，30天窗口）
# 3. 回购/增持/收购事件采集
# 4. 连跌检测 + 交叉预警
#
# 依赖：
# - .venv 激活的 Python 环境
# - packages/ 三个数据包
# - DuckDB 数据库路径由 .env 控制
# - akshare 可用

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# 单个命令超时（秒），防止网络慢或 OOM 卡死整条链
TIMEOUT=600

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/data-packages-collect.log"

# PID 文件防并发（当 launchd 触发时，若前次仍在运行则跳过）
PIDFILE="$ROOT/data/data_packages_collect.pid"
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE" 2>/dev/null)" 2>/dev/null; then
  log "[前置] 另一采集进程仍在运行（pid=$(cat "$PIDFILE")），本次跳过"
  exit 0
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

# 加载 .env（若存在）
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

VENV_PYTHON="$ROOT/.venv/bin/python3"
if [ ! -x "$VENV_PYTHON" ]; then
  VENV_PYTHON="python3"
fi

# PYTHONPATH 统一
export PYTHONPATH="packages/financial-report/src:packages/rumor-capture/src:packages/buyback-alert/src:."

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== newhigh 数据增量采集 开始 ==="

# ---- 1. 财报采集（前100只A股：逐步覆盖；固定 limit 避免 OOM）----
log "[财报] 开始批量采集..."
gtimeout $TIMEOUT $VENV_PYTHON -m financial_report --batch --limit 100 >> "$LOG_FILE" 2>&1 || log "[财报] ⚠️ 超时或失败（exit=$?）"
log "[财报] 采集完成"

# ---- 2. 传闻采集 ----
log "[传闻] 开始雪球采集..."
gtimeout $TIMEOUT $VENV_PYTHON -m rumor_capture --source xueqiu --days 30 >> "$LOG_FILE" 2>&1 || log "[传闻] ⚠️ 雪球超时或失败（exit=$?）"
log "[传闻] 雪球完成"

log "[传闻] 开始 news_items 回溯..."
gtimeout $TIMEOUT $VENV_PYTHON -m rumor_capture --source news --days 30 >> "$LOG_FILE" 2>&1 || log "[传闻] ⚠️ news_items 超时或失败（exit=$?）"
log "[传闻] news_items 完成"

# ---- 3. 回购/收购事件采集 ----
log "[回购] 开始事件采集..."
gtimeout $TIMEOUT $VENV_PYTHON -m buyback_alert --collect >> "$LOG_FILE" 2>&1 || log "[回购] ⚠️ 超时或失败（exit=$?）"
log "[回购] 事件采集完成"

# ---- 4. 连跌 + 预警 ----
log "[预警] 开始连跌检测 + 交叉分析..."
gtimeout $TIMEOUT $VENV_PYTHON -m buyback_alert --detect --alert >> "$LOG_FILE" 2>&1 || log "[预警] ⚠️ 超时或失败（exit=$?）"
log "[预警] 连跌+交叉分析完成"

# ---- 汇总 ----
log "[汇总] 查看各表行数..."
$VENV_PYTHON -c "
import duckdb, os
db = os.environ.get('QUANT_SYSTEM_DUCKDB_PATH', 'data/quant_system.duckdb')
con = duckdb.connect(db, read_only=True)
for t in ['financial_reports', 'company_rumors', 'buyback_events', 'alerts']:
    cnt = con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]
    print(f'  {t}: {cnt} 行')
con.close()
" 2>&1 | tee -a "$LOG_FILE"

log "=== 数据增量采集 完成 ==="
