#!/usr/bin/env bash
# 检查良性闭环前置条件：openclaw、cursor、规划脚本可跑；提示 CURSOR_API_KEY / login。
# 用法：bash scripts/check_openclaw_cursor_loop.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

echo "=== 1. 可执行文件 ==="
for c in openclaw cursor; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "  OK: $c -> $(command -v "$c")"
  else
    echo "  缺失: $c（请安装 Cursor CLI 与 OpenClaw）" >&2
    exit 1
  fi
done

if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi

echo "=== 2. Cursor 认证（二选一）==="
if [[ -n "${CURSOR_API_KEY:-}" ]]; then
  echo "  OK: 已设置 CURSOR_API_KEY（来自环境或 .env）"
else
  echo "  未设置 CURSOR_API_KEY。请任选其一："
  echo "    (1) 在仓库根 .env 增加一行: CURSOR_API_KEY=你的密钥"
  echo "    (2) 终端执行: cursor agent login"
fi

echo "=== 3. OpenClaw 规划（冒烟，约 1～3 分钟）==="
export OPENCLAW_CURSOR_PLAN_ONLY=1
export OPENCLAW_ITERATION_TIMEOUT_SEC="${OPENCLAW_ITERATION_TIMEOUT_SEC:-120}"
if bash "$ROOT/scripts/openclaw_cursor_iterate.sh" >/dev/null; then
  echo "  OK: 已生成 evolution/openclaw_cursor_last_plan.md"
else
  echo "  失败: 规划步骤异常" >&2
  exit 1
fi

echo "=== 4. 下一步 ==="
echo "  若已 login 或已配置 CURSOR_API_KEY，执行:"
echo "    cd $ROOT && make openclaw-benign-loop"
echo "  若只想反复生成规划（不跑 Cursor）:"
echo "    OPENCLAW_CURSOR_PLAN_ONLY=1 make openclaw-benign-loop"
