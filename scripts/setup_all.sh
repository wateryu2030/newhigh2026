#!/usr/bin/env bash
# 一键初始化脚本
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "🚀 开始一键初始化..."
echo ""

if [[ ! -d venv ]]; then
  echo "创建虚拟环境..."
  python3 -m venv venv
fi

source venv/bin/activate

echo "安装依赖..."
pip install -e ./akshare -q
pip install -e ./rqalpha -q
pip install flask -q

echo "运行完整初始化..."
python setup_complete.py

echo ""
echo "✅ 初始化完成！"
echo ""
echo "下一步:"
echo "1. 测试数据: python test_wentai.py"
echo "2. 启动平台: python web_platform.py"
echo "3. 运行回测: python run_backtest.py strategies/strategy_wentai_demo.py 2024-01-01 2024-06-30"
