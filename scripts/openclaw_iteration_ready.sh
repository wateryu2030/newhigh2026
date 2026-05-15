#!/usr/bin/env bash
# 一键：OpenClaw 按设计做「调度 + 文档迭代」前的本机准备（仓库根执行）
# - 工作区 symlink、同步 HEARTBEAT
# - addyosmani skills（PATH 用 Homebrew node）
# - 自检 symlink / HEARTBEAT / CLI
# 飞书 Cron 须改通道、UI 须开 Agent 等：见文末输出与 docs/OPENCLAW_FEISHU_DELIVERY_TARGET.md
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== [1/3] workspace + HEARTBEAT ==="
bash "$ROOT/scripts/openclaw_workspace_bootstrap.sh"

echo ""
echo "=== [2/3] addyosmani skills ==="
bash "$ROOT/scripts/install_openclaw_addyosmani_skills.sh"

echo ""
echo "=== [3/3] smoke ==="
WS="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
ok=0
if [[ -L "$WS/newhigh" ]] || [[ -d "$WS/newhigh" ]]; then
  echo "[OK] $WS/newhigh -> $(readlink "$WS/newhigh" 2>/dev/null || echo dir)"
  ok=$((ok + 1))
else
  echo "[WARN] 缺少 $WS/newhigh，请检查 symlink"
fi
if [[ -f "$WS/HEARTBEAT.md" ]]; then
  echo "[OK] HEARTBEAT.md 存在"
  ok=$((ok + 1))
else
  echo "[WARN] 缺少 $WS/HEARTBEAT.md"
fi
if command -v openclaw >/dev/null 2>&1; then
  echo "[OK] openclaw CLI: $(command -v openclaw)"
  ok=$((ok + 1))
else
  echo "[INFO] 未在 PATH 找到 openclaw（可选，用于 cron / message send）"
fi

echo ""
echo "=== 本机准备完成（脚本部分）==="
echo "请手动完成（无法脚本代劳）："
echo "  1) OpenClaw Web：会话改为「带工具/Agent」；Cron 投递若报 Feishu target → 改为 webchat --to last 或配齐飞书（见 docs/OPENCLAW_FEISHU_DELIVERY_TARGET.md）"
echo "  2) 重启 OpenClaw Gateway / App，使 HEARTBEAT 与 skills 生效"
echo "  3) Cursor：打开 $ROOT ，先读 tasks/openclaw_handoff.md 与 tasks/current_task.md"
echo ""
echo "编排索引：docs/OPENCLAW_ORCHESTRATION.md"
