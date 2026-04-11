#!/usr/bin/env bash
# Next output: 'standalone' 时必须把 .next/static 与 public 同步到 standalone 目录，
# 否则公网 /_next/static/chunks/*（含 app-pages-internals.js）会 404。
# 用法：在 frontend 目录下由 npm run start:standalone 调用。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .next/BUILD_ID ]]; then
  echo "[standalone] 缺少 .next/BUILD_ID，请先执行: npm run build" >&2
  exit 1
fi
if [[ ! -d .next/static ]] || [[ -z "$(ls -A .next/static 2>/dev/null)" ]]; then
  echo "[standalone] 缺少或为空 .next/static，请重新执行: npm run build" >&2
  exit 1
fi
if [[ ! -f .next/standalone/server.js ]]; then
  echo "[standalone] 缺少 .next/standalone/server.js，请先执行: npm run build" >&2
  exit 1
fi

mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
mkdir -p .next/standalone/.next/static
cp -R .next/static/. .next/standalone/.next/static/

if [[ -d public ]]; then
  rm -rf .next/standalone/public
  cp -R public .next/standalone/public
fi

cp -f .next/BUILD_ID .next/standalone/.next/BUILD_ID 2>/dev/null || true

cnt="$(find .next/standalone/.next/static -type f 2>/dev/null | wc -l | tr -d ' ')"
echo "[standalone] 已同步静态文件 ${cnt} 个 → .next/standalone/.next/static"

exec env PORT="${PORT:-3000}" HOSTNAME="${HOSTNAME:-0.0.0.0}" node .next/standalone/server.js
