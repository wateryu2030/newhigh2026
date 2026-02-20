#!/usr/bin/env bash
# 在 astock 项目根目录执行，自动激活 venv 并运行 akshare 示例
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -d venv ]]; then
  echo "未找到 venv，请先执行: python3 -m venv venv && source venv/bin/activate && pip install -e ./akshare"
  exit 1
fi
source venv/bin/activate
exec python run_akshare.py "$@"
