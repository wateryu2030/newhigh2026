#!/usr/bin/env bash
# 将仓库内的 OpenClaw 自主迭代 HEARTBEAT 模板同步到 ~/.openclaw/workspace/HEARTBEAT.md
# 使用前请确认已安装 OpenClaw 且工作区路径存在。

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/docs/openclaw/HEARTBEAT_AUTONOMOUS.md"
DST_DIR="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
DST="${DST_DIR}/HEARTBEAT.md"

if [[ ! -f "$SRC" ]]; then
  echo "missing: $SRC" >&2
  exit 1
fi
mkdir -p "$DST_DIR"
if [[ -f "$DST" ]]; then
  cp -a "$DST" "${DST}.bak.$(date +%Y%m%d%H%M%S)"
  echo "backed up existing HEARTBEAT.md"
fi
cp -a "$SRC" "$DST"
echo "synced: $SRC -> $DST"
echo "OpenClaw Heartbeat/Cron 将读取该文件。恢复备份请查看 ${DST_DIR}/HEARTBEAT.md.bak.*"
