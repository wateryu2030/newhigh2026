#!/bin/bash
# 重新构建前端并启动 Web 平台（确保最新改动生效）
set -e
cd "$(dirname "$0")/.."
echo ">>> 构建前端..."
cd frontend && npm run build && cd ..
echo ">>> 启动 Web 平台 (http://127.0.0.1:5050)..."
echo "    市场扫描器: 点击表头可排序，点击行可查看详情与 K 线"
echo "    按 Ctrl+C 停止"
exec python3 web_platform.py
