#!/usr/bin/env bash
# OpenClaw 本机快速探活（不修改配置）。仓库根：可与 newhigh 无关，仅检查本机。
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

echo "=== openclaw CLI ==="
if command -v openclaw >/dev/null 2>&1; then
  openclaw --version 2>&1 || true
else
  echo "未找到 openclaw（PATH 需含 Homebrew）"
fi

echo ""
echo "=== Gateway :18789（若未运行会失败）==="
curl -sf -o /dev/null -w "HTTP %{http_code}\n" "http://127.0.0.1:18789/" 2>/dev/null || echo "无法连接 127.0.0.1:18789（Gateway 可能未启动）"

echo ""
echo "=== 工作区 symlink ==="
WS="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
if [[ -e "$WS/newhigh" ]]; then
  ls -la "$WS/newhigh" 2>/dev/null || true
else
  echo "缺少 $WS/newhigh — 运行: make openclaw-iterate-ready"
fi

echo ""
echo "=== HEARTBEAT ==="
[[ -f "$WS/HEARTBEAT.md" ]] && echo "存在: $WS/HEARTBEAT.md" || echo "缺失 HEARTBEAT.md"

echo ""
echo "=== openclaw doctor（前 40 行）==="
if command -v openclaw >/dev/null 2>&1; then
  openclaw doctor 2>&1 | head -40 || true
else
  echo "跳过（无 CLI）"
fi

echo ""
echo "详细改进清单: docs/OPENCLAW_REALITY_CHECK_AND_IMPROVEMENTS.md"
