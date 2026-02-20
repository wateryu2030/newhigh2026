#!/bin/bash
# 快速测试简单策略（推荐首次使用）

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "=========================================="
echo "快速测试：通用均线策略 + 600745"
echo "=========================================="
echo ""

python run_backtest_db.py strategies/universal_ma_strategy.py 2024-01-01 2024-01-31

echo ""
echo "=========================================="
echo "如果上述回测成功，说明系统正常"
echo "可以继续在 Web 平台测试其他策略"
echo "=========================================="
