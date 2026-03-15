#!/usr/bin/env bash
# 代码规范与测试自动化：W0407 导入别名、C0301 长行、全量测试
# 用法：在仓库根目录执行 bash scripts/run_quality_automation.sh

set -e
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true

echo "=== 1. 格式化（autopep8 + black）==="
python -m autopep8 --in-place --aggressive --max-line-length 100 \
  data-engine/src/data_engine/*.py \
  strategy-engine/src/strategy_engine/*.py \
  2>/dev/null || true
if command -v black &>/dev/null; then
  black --line-length 100 \
    data-engine/src/data_engine/connector_astock_duckdb.py \
    data-engine/src/data_engine/data_pipeline.py \
    strategy-engine/src/strategy_engine/ai_fusion_strategy.py \
    2>/dev/null || true
fi

echo "=== 2. Pylint 抽检（data-engine 关键文件）==="
pylint data-engine/src/data_engine/connector_akshare.py \
  data-engine/src/data_engine/connector_tushare.py \
  data-engine/src/data_engine/connector_astock_duckdb.py \
  --output-format=text 2>&1 | tail -5

echo "=== 3. 全量测试 ==="
bash scripts/run_tests.sh

echo "=== 完成 ==="
