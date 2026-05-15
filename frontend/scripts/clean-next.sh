#!/usr/bin/env bash
# 彻底删除 .next（解决 standalone 嵌套 node_modules 导致 rm 报 Directory not empty）
# 用法：在 frontend/ 下 npm run 已带 cd；也可 bash frontend/scripts/clean-next.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"
if [[ -d .next ]]; then
  chmod -R u+w .next 2>/dev/null || true
  rm -rf .next
fi
echo "[clean-next] removed $HERE/.next"
