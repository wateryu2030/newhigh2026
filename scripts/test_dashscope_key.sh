#!/usr/bin/env bash
# 验证百炼 API Key（支持 Coding Plan 与 兼容模式）
# 使用：bash scripts/test_dashscope_key.sh
# 可选：DASHSCOPE_BASE_URL=https://coding.dashscope.aliyun.com/v1 bash scripts/test_dashscope_key.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ -z "$DASHSCOPE_API_KEY" ] && [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env" 2>/dev/null || true
  set +a
fi
if [ -z "$DASHSCOPE_API_KEY" ]; then
  echo "错误: 未设置 DASHSCOPE_API_KEY。请在 .env 中配置或执行: DASHSCOPE_API_KEY=sk-xxx $0"
  exit 1
fi
# Coding Plan 套餐用 coding.dashscope.aliyuncs.com/v1；兼容模式用 dashscope.aliyuncs.com/compatible-mode/v1
BASE_URL="${DASHSCOPE_BASE_URL:-https://coding.dashscope.aliyuncs.com/v1}"
echo "使用 Key 前缀: ${DASHSCOPE_API_KEY:0:12}..."
echo "Base URL: $BASE_URL"
RESP=$(curl -s -w "\n%{http_code}" --max-time 30 \
  -X POST "${BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
  -d '{"model":"qwen3.5-plus","messages":[{"role":"user","content":"Hi"}],"max_tokens":32}')
CODE=$(echo "$RESP" | tail -n 1)
BODY=$(echo "$RESP" | sed '$d')
if [ "$CODE" = "200" ]; then
  echo "百炼 API Key 有效，请求成功 (HTTP 200)。"
  echo "$BODY" | head -c 200
  echo ""
  exit 0
fi
echo "请求失败 (HTTP $CODE)。"
echo "  - 401: Key 或 Base URL 不匹配（Coding Plan 需用 https://coding.dashscope.aliyuncs.com/v1）"
echo "  - 超时: 网络/VPN 可能影响，可尝试关闭 VPN 或设置 NO_PROXY=*.aliyuncs.com"
echo "响应摘要: ${BODY:0:300}"
exit 1
