#!/usr/bin/env bash
# OpenClaw 开发向环境：工作区 symlink + HEARTBEAT + addyosmani skills（§4.1）
# 会话模式 / UI 内启用 Skills 须手动，见 docs/OPENCLAW_AUTONOMOUS_DEVELOPMENT_SETUP.md §4.2
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/openclaw_workspace_bootstrap.sh"
bash "$ROOT/scripts/install_openclaw_addyosmani_skills.sh"
echo ""
echo "[openclaw_dev_environment_setup] 完成。请重启 OpenClaw，并在 UI 中开启带 Agent/工具的会话模式（§4.2）。"
