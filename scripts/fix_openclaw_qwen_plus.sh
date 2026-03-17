#!/usr/bin/env bash
# 自动处理 OpenClaw「400 model qwen-plus is not supported」：
# 从 ~/.openclaw/openclaw.json 移除 qwen-plus 模型项与 fallback。
# 使用：bash scripts/fix_openclaw_qwen_plus.sh
#       bash scripts/fix_openclaw_qwen_plus.sh --restart-gateway

set -e
OPENCLAW_JSON="${OPENCLAW_JSON:-$HOME/.openclaw/openclaw.json}"
RESTART_GATEWAY=false
[[ "${1:-}" == "--restart-gateway" ]] && RESTART_GATEWAY=true

if [[ ! -f "$OPENCLAW_JSON" ]]; then
  echo "未找到 $OPENCLAW_JSON，跳过修复。"
  exit 0
fi
export OPENCLAW_JSON

python3 << PY
import json
import os
path = os.environ.get("OPENCLAW_JSON", os.path.expanduser("~/.openclaw/openclaw.json"))
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
changed = False
if "models" in data and "providers" in data["models"] and "dashscope" in data["models"]["providers"]:
    models = data["models"]["providers"]["dashscope"].get("models", [])
    new_models = [m for m in models if m.get("id") != "qwen-plus"]
    if len(new_models) != len(models):
        data["models"]["providers"]["dashscope"]["models"] = new_models
        changed = True
if "agents" in data and "defaults" in data["agents"] and "model" in data["agents"]["defaults"]:
    fallbacks = data["agents"]["defaults"]["model"].get("fallbacks", [])
    new_fb = [f for f in fallbacks if f != "dashscope/qwen-plus"]
    if len(new_fb) != len(fallbacks):
        data["agents"]["defaults"]["model"]["fallbacks"] = new_fb
        changed = True
if "agents" in data and "defaults" in data["agents"] and "models" in data["agents"]["defaults"]:
    if "dashscope/qwen-plus" in data["agents"]["defaults"]["models"]:
        del data["agents"]["defaults"]["models"]["dashscope/qwen-plus"]
        changed = True
if changed:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("已从 openclaw.json 移除 qwen-plus 相关配置")
else:
    print("openclaw.json 中已无 qwen-plus 引用，无需修改")
PY

if [[ "$RESTART_GATEWAY" == true ]]; then
  echo "正在重启 OpenClaw Gateway..."
  launchctl bootout "gui/$(id -u)/ai.openclaw.gateway" 2>/dev/null || true
  sleep 2
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/ai.openclaw.gateway.plist" 2>/dev/null || true
  echo "Gateway 已重启，请稍等几秒后新开会话再试。"
fi
echo "处理完成。若仍报 400，请完全退出 OpenClaw 后重新打开并新开会话。"
