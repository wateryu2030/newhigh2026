#!/usr/bin/env python3
"""
修复 OpenClaw「All models failed」中因上下文不足导致的失败：
- 豆包 4K、Kimi 8K 的 context 仅 4k/8k，心跳等任务常需 16k+，会报 Model context window too small。
- 将 fallbacks 改为仅使用 16k+ 上下文的模型，避免轮到 4k/8k 时必败。

用法：python scripts/fix_openclaw_fallbacks.py
会备份 ~/.openclaw/openclaw.json 后修改 agents.defaults.model.fallbacks。
修改后需重启 Gateway：./scripts/restart_newhigh_bot.sh
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

OPENCLAW_JSON = Path.home() / ".openclaw" / "openclaw.json"

# 仅保留 context >= 32k 的模型，避免 "Minimum is 16000" 报错
FALLBACKS_LARGE_CONTEXT = [
    "dashscope/qwen3.5-plus",
    "dashscope/qwen3-coder-next",
    "deepseek/deepseek-chat",
    "deepseek/deepseek-coder",
    "moonshot/moonshot-v1-32k",
    "openai/gpt-4o-mini",
]


def main() -> None:
    if not OPENCLAW_JSON.exists():
        print(f"❌ 未找到 {OPENCLAW_JSON}")
        return
    path = OPENCLAW_JSON
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    agents = data.get("agents") or {}
    defaults = agents.get("defaults") or {}
    model_cfg = defaults.get("model") or {}
    old_fallbacks = model_cfg.get("fallbacks") or []

    if old_fallbacks == FALLBACKS_LARGE_CONTEXT:
        print("✅ fallbacks 已是仅大上下文模型，无需修改")
        return

    backup = path.with_suffix(path.suffix + ".bak_fallbacks")
    shutil.copy2(path, backup)
    print(f"📦 已备份到 {backup}")

    if "defaults" not in data["agents"]:
        data["agents"]["defaults"] = {}
    if "model" not in data["agents"]["defaults"]:
        data["agents"]["defaults"]["model"] = {}
    data["agents"]["defaults"]["model"]["fallbacks"] = FALLBACKS_LARGE_CONTEXT

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ 已更新 fallbacks 为仅大上下文模型（≥32k）：")
    for m in FALLBACKS_LARGE_CONTEXT:
        print(f"   - {m}")
    print("🔄 请执行重启使配置生效：./scripts/restart_newhigh_bot.sh")


if __name__ == "__main__":
    main()
