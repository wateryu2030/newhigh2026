#!/bin/bash
# 同步闻泰科技数据到数据库

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "开始同步闻泰科技（600745）数据..."
python database/sync_data.py --wentai

echo ""
echo "✅ 数据同步完成！"
echo "可以使用以下命令运行回测："
echo "  python run_backtest_db.py strategies/strategy_wentai_demo.py 2024-01-01 2024-12-31"
