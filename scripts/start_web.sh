#!/bin/bash
# 启动量化平台 Web 服务（优先使用 venv，默认 5050 端口）
cd "$(dirname "$0")/.."
ROOT="$PWD"
PORT="${PORT:-5050}"

if [ -d "$ROOT/venv" ]; then
  . "$ROOT/venv/bin/activate"
elif [ -d "$ROOT/.venv" ]; then
  . "$ROOT/.venv/bin/activate"
fi

export PORT
echo "Starting at http://127.0.0.1:$PORT (PORT=$PORT)"
exec python3 web_platform.py
