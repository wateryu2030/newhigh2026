#!/usr/bin/env bash
# 良性闭环：OpenClaw（local 规划）→ 写入规划文件 → Cursor CLI 执行。
# 勿用 OpenClaw Web + DeepSeek 连续 read 仓库文件（易陷入复读）；本脚本走终端、无 Web 工具链。
#
# 用法（仓库根）：
#   bash scripts/openclaw_benign_loop.sh
#   OPENCLAW_CURSOR_PLAN_ONLY=1 bash scripts/openclaw_benign_loop.sh   # 只生成规划，不跑 cursor agent
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash "$ROOT/scripts/openclaw_cursor_iterate.sh"
