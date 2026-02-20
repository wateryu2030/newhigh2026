#!/usr/bin/env bash
# 准备策略数据脚本
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  echo "错误: 未找到 venv，请先执行安装步骤"
  exit 1
fi

source venv/bin/activate

echo "准备策略数据..."
echo "1. 创建数据目录"
mkdir -p data

echo "2. 运行数据获取脚本（可能需要一些时间）"
python data_prep/akshare_data_fetcher.py

echo ""
echo "数据准备完成！"
echo "数据文件保存在 data/ 目录"
echo ""
echo "注意："
echo "- 如果某些数据获取失败，可以手动创建CSV文件"
echo "- 策略1需要: data/industry_stock_map.csv 和 data/industry_score.csv"
echo "- 策略2需要: data/tech_leader_stocks.csv 和 data/consume_leader_stocks.csv"
