#!/usr/bin/env bash
# 在 frontend 子目录误跑 python3 scripts/strategy_automation.py 会找不到文件；
# 本脚本固定从仓库根调用（需已存在 ../.venv）。
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec "${ROOT}/.venv/bin/python" "${ROOT}/scripts/strategy_automation.py" "$@"
