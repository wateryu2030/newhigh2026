#!/usr/bin/env bash
# 启动量化交易平台
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  echo "错误: 未找到 venv，请先执行安装步骤"
  exit 1
fi

source venv/bin/activate

# 确保目录存在
mkdir -p strategies output

PORT="${PORT:-5050}"
echo "启动量化交易平台..."
echo "访问 http://127.0.0.1:${PORT} 使用平台"
echo "按 Ctrl+C 停止服务"
echo ""

python web_platform.py
