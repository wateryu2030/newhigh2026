#!/usr/bin/env bash
# 自检：本机 Next 是否正返回 /_next/static 资源（Tunnel 必须指向该端口，而非 Gateway :8000）。
# 会探测首页 HTML 中引用的多个 chunk（含 app-pages-internals.js 若存在）。
# 用法：bash scripts/verify_next_static_local.sh [BASE_URL]
# 默认 BASE_URL=http://127.0.0.1:3000
set -euo pipefail
BASE="${1:-http://127.0.0.1:3000}"
BASE="${BASE%/}"
echo "[verify] GET $BASE/"
html=$(curl -sf "$BASE/" | head -c 200000) || {
  echo "[verify] 失败：无法访问 $BASE/（Next 是否在跑？）" >&2
  exit 1
}
paths=$(printf '%s' "$html" | grep -oE '/_next/static/[^"'\'' <>?]+' | sort -u | head -8) || true
if [[ -z "${paths:-}" ]]; then
  echo "[verify] 警告：首页 HTML 中未匹配到 /_next/static 引用" >&2
  exit 1
fi
fail=0
while IFS= read -r path; do
  [[ -z "$path" ]] && continue
  # 去掉 query（如 ?v=）
  clean="${path%%\?*}"
  code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$clean")
  echo "[verify] $clean → HTTP $code"
  if [[ "$code" != "200" ]]; then
    fail=1
  fi
done <<< "$paths"
if [[ "$fail" -ne 0 ]]; then
  echo "[verify] 失败（常见：Tunnel 指到 8000、standalone 未正确复制 .next/static、Cloudflare 缓存旧 HTML、或 static 被误嵌套为 static/static）" >&2
  echo "[verify] 修复：cd frontend && rm -rf .next && npm run build && npm run start:standalone" >&2
  echo "[verify] 公网：Cloudflare 对 htma 做 Purge；Tunnel 主机名 → http://127.0.0.1:3000" >&2
  exit 1
fi
n=$(printf '%s\n' "$paths" | grep -c . || true)
echo "[verify] OK（已探测 ${n:-0} 条 /_next/static 引用）"
