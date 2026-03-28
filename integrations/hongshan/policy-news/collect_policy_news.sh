#!/bin/bash
# 可选：通过 OpenClaw 向飞书发送「采集开始」提示；实际采集请直接运行 news_collector.py
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HS_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOG_FILE="$HS_ROOT/logs/policy_collector_cron.log"
mkdir -p "$HS_ROOT/logs"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 定时任务入口（可选 OpenClaw 通知）" >>"$LOG_FILE"
cd "$REPO_ROOT" || exit 1
if command -v openclaw >/dev/null 2>&1; then
  openclaw message send --channel feishu --message "🔄 政策采集任务已触发（见 $(basename "$0")）" 2>>"$LOG_FILE" || true
fi
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 结束" >>"$LOG_FILE"
