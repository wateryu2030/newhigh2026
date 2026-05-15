#!/usr/bin/env bash
# OpenClaw 工作区：挂上主仓 symlink + 同步 HEARTBEAT.md（与 docs/OPENCLAW_AUTONOMOUS_DEVELOPMENT_SETUP.md 一致）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WS="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
mkdir -p "$WS"
ln -sf "$ROOT" "$WS/newhigh"
echo "[openclaw bootstrap] symlink: $WS/newhigh -> $ROOT"
bash "$ROOT/scripts/sync_openclaw_heartbeat.sh"
echo "[openclaw bootstrap] 完成。下一步在 OpenClaw UI：开启带工具/Agent 的会话、配置 Skills，见 docs/OPENCLAW_AUTONOMOUS_DEVELOPMENT_SETUP.md §四。"
