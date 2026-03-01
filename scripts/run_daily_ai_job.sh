#!/bin/bash
# 每日 AI 分析批处理：
# 1) 补齐全 A 股训练数据（DuckDB）
# 2) 训练/更新 AI 选股模型（ai_models.ModelManager）
#
# 建议由 launchd 在每天晚间 20:00 之后自动调用。

set -e

ROOT="/Users/apple/astock"
cd "$ROOT"

VENV_PY="$ROOT/.venv/bin/python3"

if [ ! -x "$VENV_PY" ]; then
  echo "找不到虚拟环境 Python: $VENV_PY"
  exit 1
fi

echo "[$(date '+%F %T')] 开始补齐 AI 训练数据..."
"$VENV_PY" scripts/ensure_ai_data.py

echo "[$(date '+%F %T')] 开始训练/更新 AI 模型..."
"$VENV_PY" train_ai_model.py

echo "[$(date '+%F %T')] AI 日终任务完成。"

