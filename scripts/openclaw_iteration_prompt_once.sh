#!/usr/bin/env bash
# 一轮「迭代开发」提示：内联 tasks/current_task.md + OPENCLAW_ORCHESTRATION §2，避免 CLI/Gateway 上 read 工具失败。
#
# 默认使用 openclaw agent --local（本机直连模型，不抢主会话锁；与 Web 并行时更稳）。
# 若必须用 Gateway：  OPENCLAW_ITERATION_LOCAL=0 bash scripts/openclaw_iteration_prompt_once.sh
#
# 用法（仓库根）：
#   bash scripts/openclaw_iteration_prompt_once.sh
# 可选：
#   NEWHIGH_ROOT=/path OPENCLAW_ITERATION_TIMEOUT_SEC=900 OPENCLAW_ITERATION_LOCAL=0 bash scripts/openclaw_iteration_prompt_once.sh
set -euo pipefail
REPO="${NEWHIGH_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"
TIMEOUT_SEC="${OPENCLAW_ITERATION_TIMEOUT_SEC:-600}"
USE_LOCAL="${OPENCLAW_ITERATION_LOCAL:-1}"

CT_FILE="$REPO/tasks/current_task.md"
ORCH="$REPO/docs/OPENCLAW_ORCHESTRATION.md"
if [[ ! -f "$CT_FILE" || ! -f "$ORCH" ]]; then
  echo "缺少文件: $CT_FILE 或 $ORCH" >&2
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

# 与 Makefile / docs/OPENCLAW_ORCHESTRATION.md §4 一致：优先用仓库 .venv，避免 PATH 无 python3 或系统解释器过旧。
if [[ -x "$REPO/.venv/bin/python" ]]; then
  PYTHON_BIN=( "$REPO/.venv/bin/python" )
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN=( python3 )
else
  echo "未找到 Python：请安装 python3 或创建 $REPO/.venv（见仓库 README / make pipeline-editable）" >&2
  exit 1
fi

"${PYTHON_BIN[@]}" <<PY > "$TMP"
from pathlib import Path

repo = Path(r"""$REPO""")
current = Path(r"""$CT_FILE""").read_text(encoding="utf-8")
text = (repo / "docs" / "OPENCLAW_ORCHESTRATION.md").read_text(encoding="utf-8")
a = text.find("## 2. 任务选取规则")
b = text.find("## 3.", a) if a != -1 else -1
orch2 = text[a:b] if a != -1 and b != -1 else "(未能截取 §2，请人工打开 docs/OPENCLAW_ORCHESTRATION.md)\n"

body = f"""你是 newhigh 迭代助手。主仓：{repo}

【重要】下列正文已从仓库直接粘贴，你无需再调用 read 打开这些路径；请仅根据下文与常识作答。

--- tasks/current_task.md ---
{current}

--- docs/OPENCLAW_ORCHESTRATION.md（§2 起至 §3 前）---
{orch2}

【约束】只做 1 条最小可验证 P0/P1；禁止写入 token/密钥；默认不真实下单；改动保持仓库风格。

【验证约定】写「验证命令」时请遵守本仓库习惯：使用 **python3**（勿写 `python`）；需要导入 data_pipeline 时 **PYTHONPATH** 含 `data-pipeline/src`、`core/src`（或说明先 `pip install -e ./data-pipeline`）；pytest 用 **`.venv/bin/python -m pytest`**；网关冒烟：**`pytest gateway/tests/`**（仓库根）。

【产出】用 Markdown 分节输出：
1. 所选任务（一句话 + 文档引用）
2. 涉及文件路径
3. 建议改动（若不能写仓库则写成给 Cursor 的步骤清单）
4. 验证命令（仓库根可执行）
5. 风险与回滚（各一句）
6. 需 Cursor 接手项（若有）

禁止空洞总结与仅 HEARTBEAT_OK。
"""
print(body, end="")
PY

MSG="$(cat "$TMP")"
if [[ "$USE_LOCAL" == "1" ]]; then
  exec openclaw agent --local --agent main --timeout "${TIMEOUT_SEC}" --message "${MSG}"
else
  exec openclaw agent --agent main --timeout "${TIMEOUT_SEC}" --message "${MSG}"
fi
