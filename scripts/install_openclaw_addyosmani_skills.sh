#!/usr/bin/env bash
# 将 addyosmani/agent-skills 装到本机（与具体 Git 项目无关）。
# npx skills --global 实际布局：实体在 ~/.agents/skills/，OpenClaw 侧为 ~/.openclaw/skills/ 下符号链接。
# 自定义技能仍可放 ~/.openclaw/workspace/skills/（与 addyosmani 包并存）。
#
# 用法：
#   bash scripts/install_openclaw_addyosmani_skills.sh
# 可选：仅克隆、跳过 npx
#   OPENCLAW_SKILLS_USE_GIT_ONLY=1 bash scripts/install_openclaw_addyosmani_skills.sh
#
# 说明：
# - 请使用 Homebrew 的 node/npx（PATH 前置 /opt/homebrew/bin），避免 ~/.local/bin/npx 指向已删除的 node。
# - 安装后建议重启 OpenClaw Gateway（见 docs/OPENCLAW_运行说明.md）。
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

WS="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
SK_ROOT="${WS}/skills"
REPO_URL="${ADDYOSMANI_AGENT_SKILLS_URL:-https://github.com/addyosmani/agent-skills.git}"
TARGET_DIR="${SK_ROOT}/agent-skills"

mkdir -p "$SK_ROOT"

use_git_only() {
  [[ "${OPENCLAW_SKILLS_USE_GIT_ONLY:-0}" == "1" ]]
}

if use_git_only || ! command -v npx >/dev/null 2>&1; then
  echo "[install] 使用 git shallow clone → $TARGET_DIR"
  rm -rf "$TARGET_DIR"
  git clone --depth 1 "$REPO_URL" "$TARGET_DIR"
  echo "[install] 完成。目录: $TARGET_DIR"
  exit 0
fi

echo "[install] 尝试 npx skills（工作目录: $WS）…"
cd "$WS"
if npx --yes skills add addyosmani/agent-skills --yes --global; then
  echo "[install] npx skills 完成。"
  # OpenClaw 会从 ~/.agents/skills 直接加载（agents-skills-personal）。npx 在 ~/.openclaw/skills
  # 下创建的、指向 ~/.agents 的 symlink 会触发「resolves outside configured root」告警，删除重复链接即可。
  OC_SK="$HOME/.openclaw/skills"
  if [[ -d "$OC_SK" ]]; then
    find "$OC_SK" -maxdepth 1 -type l 2>/dev/null | while IFS= read -r link; do
      [[ -z "$link" ]] && continue
      t=$(readlink "$link" 2>/dev/null || true)
      case "$t" in
        *".agents/skills"*) rm -f "$link" && echo "[install] 已移除重复 symlink（OpenClaw 仍从 ~/.agents/skills 加载）: $(basename "$link")" ;;
      esac
    done
  fi
else
  echo "[install] npx 失败，回退 git clone…"
  rm -rf "$TARGET_DIR"
  git clone --depth 1 "$REPO_URL" "$TARGET_DIR"
  echo "[install] git 完成。目录: $TARGET_DIR"
fi

echo "[install] 当前 skills 根目录列表:"
ls -la "$SK_ROOT" 2>/dev/null || true
