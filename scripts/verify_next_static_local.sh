#!/usr/bin/env bash
# 自检：本机 Next 是否正返回 /_next/static 资源（Tunnel 必须指向该端口，而非 Gateway :8000）。
# 用法：bash scripts/verify_next_static_local.sh [BASE_URL]
# 默认 BASE_URL=http://127.0.0.1:3000
set -euo pipefail
BASE="${1:-http://127.0.0.1:3000}"
BASE="${BASE%/}"
echo "[verify] GET $BASE/"
html=$(curl -sf "$BASE/" | head -c 120000) || {
  echo "[verify] 失败：无法访问 $BASE/（Next 是否在跑？）" >&2
  exit 1
}
# 取第一个 css / chunks js 引用
path=$(printf '%s' "$html" | grep -oE '/_next/static/[^"'\'' <>]+' | head -1) || true
if [[ -z "${path:-}" ]]; then
  echo "[verify] 警告：首页 HTML 中未匹配到 /_next/static 引用"
  exit 0
fi
echo "[verify] 探测静态资源: $path"
code=$(curl -s -o /dev/null -w '%{http_code}' "$BASE$path")
if [[ "$code" != "200" ]]; then
  echo "[verify] 失败: $BASE$path → HTTP $code（常见原因：Tunnel 指到了 8000、standalone 未复制 .next/static、或 Cloudflare 缓存了旧 HTML）" >&2
  exit 1
fi
echo "[verify] OK $path → 200"
