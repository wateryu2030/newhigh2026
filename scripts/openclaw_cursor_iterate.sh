#!/usr/bin/env bash
# OpenClaw（local 规划）+ Cursor CLI（agent 改仓库）一键串联，用于自动化迭代。
#
# 前置：
#   - openclaw 已安装；本机已登录 Cursor CLI：`cursor agent login`（或设 CURSOR_API_KEY）
#   - 规划阶段默认与 scripts/openclaw_iteration_prompt_once.sh 相同（内联 current_task + §2）
#
# 用法（仓库根）：
#   bash scripts/openclaw_cursor_iterate.sh
#
# 仅生成规划文件、不调用 Cursor：
#   OPENCLAW_CURSOR_PLAN_ONLY=1 bash scripts/openclaw_cursor_iterate.sh
#
# Cursor 不加 -f（不自动放行危险命令，更保守；可能停在确认处）：
#   CURSOR_AGENT_FORCE=0 bash scripts/openclaw_cursor_iterate.sh
#
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

# 加载仓库根 .env（本地存在时），使 CURSOR_API_KEY 等对「无需交互」的 CLI 生效；勿将 .env 提交到 git。
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi

PLAN_REL="evolution/openclaw_cursor_last_plan.md"
# 勿用变量名 PLAN：用户 .env 可能含同名项，source 后会覆盖/清空导致 set -u 报错
OPENCLAW_PLAN_ABS="$ROOT/$PLAN_REL"
mkdir -p "$(dirname "$OPENCLAW_PLAN_ABS")"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "未找到 openclaw（PATH 需含 Homebrew）" >&2
  exit 1
fi
if ! command -v cursor >/dev/null 2>&1; then
  echo "未找到 cursor CLI（请安装 Cursor 并确保 cursor 在 PATH）" >&2
  exit 1
fi

echo "=== [1/2] OpenClaw local：生成迭代规划 → $PLAN_REL ===" >&2
TMP_PLAN="$(mktemp)"
{
  echo "# OpenClaw → Cursor 迭代规划"
  echo ""
  echo "生成时间: $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo ""
  echo "---"
  echo ""
  set +e
  bash "$ROOT/scripts/openclaw_iteration_prompt_once.sh" 2>/dev/null
  OWL_RC=$?
  set -e
  if [[ "$OWL_RC" != "0" ]]; then
    echo ""
    echo "(openclaw_iteration_prompt_once 退出码: $OWL_RC)"
  fi
} > "$TMP_PLAN"
if [[ ! -s "$TMP_PLAN" ]]; then
  echo "OpenClaw 未产生任何输出，已中止" >&2
  rm -f "$TMP_PLAN"
  exit 1
fi
mv "$TMP_PLAN" "$OPENCLAW_PLAN_ABS"

if [[ -n "${OPENCLAW_CURSOR_PLAN_ONLY:-}" ]]; then
  echo "已写入 ${OPENCLAW_PLAN_ABS}（跳过 Cursor）。可手动：cursor agent -p -f --workspace ${ROOT} \"阅读 ${PLAN_REL} 并按其中步骤执行\"" >&2
  echo "${OPENCLAW_PLAN_ABS}"
  exit 0
fi

FORCE=( )
if [[ "${CURSOR_AGENT_FORCE:-1}" == "1" ]]; then
  FORCE=( -f )
fi

if [[ ${#FORCE[@]} -gt 0 ]]; then
  echo "=== [2/2] Cursor agent：按规划改仓库（--print，-f）===" >&2
else
  echo "=== [2/2] Cursor agent：按规划改仓库（--print，无 -f）===" >&2
fi

# 在主 shell 内拼接 PROMPT（避免 $(cat <<EOF) 子 shell + set -u 在 bash 3.2 下误报 PLAN_REL?）
printf -v PROMPT '%s\n' \
  '你是本仓库的自动化执行代理。工作区目录即仓库根。' \
  '' \
  "请阅读相对路径「${PLAN_REL}」全文（相对当前工作区根）。其中是 OpenClaw 给出的迭代规划。" \
  '' \
  '要求：' \
  '1. 只落实其中 **1 条**最小可验证 P0/P1；若有多条建议，选风险最低、改动最小的一条。' \
  '2. 直接修改代码/配置（不要只写计划）；遵守仓库风格；禁止把 token、私钥写入仓库。' \
  '3. 若规划里写了「验证命令」，在仓库根尝试执行（失败则说明原因，不要无限重试）。' \
  '4. 最后用中文简要说明：改了哪些文件、验证结果、是否还需人类在 Cursor 里收尾。' \
  '' \
  '若某文件路径不存在，先列出目录再决定替代方案，不要臆造路径。'

if [[ -z "${CURSOR_API_KEY:-}" ]]; then
  echo "提示：未检测到 CURSOR_API_KEY。若下一步报错 Authentication，请先执行: cursor agent login" >&2
fi

if ! cursor agent -p "${FORCE[@]}" --workspace "$ROOT" "$PROMPT"; then
  echo "" >&2
  echo "Cursor agent 失败。常见原因：未登录。请在本机执行一次:" >&2
  echo "  cursor agent login" >&2
  echo "或设置环境变量 CURSOR_API_KEY（见 Cursor 文档）。规划文件已生成: ${OPENCLAW_PLAN_ABS}" >&2
  exit 1
fi
