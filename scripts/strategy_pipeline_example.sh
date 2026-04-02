#!/usr/bin/env bash
set -euo pipefail
# 策略流水线 HTTP 示例（对外开放产品语义）
# - 已登录用户：POST /api/strategies/pipeline/run
# - admin：POST /api/strategies/pipeline/jobs/{job_id}/approve（可选 X-Pipeline-Approve-Key）
#
# 用法：
#   export GATEWAY="${GATEWAY:-http://127.0.0.1:8000}"
#   export JWT="eyJ..."   # 登录后 localStorage 或 /api/auth/login 返回的 token
#   bash scripts/strategy_pipeline_example.sh
#
# 依赖：curl；可选 jq 美化输出（无 jq 则原样打印）

BASE="${GATEWAY:-http://127.0.0.1:8000}"
BASE="${BASE%/}"
AUTH_HEADER=()
if [[ -n "${JWT:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${JWT}")
else
  echo "请设置 JWT（Bearer token）" >&2
  exit 1
fi

_json() {
  if command -v jq >/dev/null 2>&1; then jq .; else cat; fi
}

echo "== 提交流水线（仅进化，小样本） =="
RUN_OUT="$(curl -sS "${AUTH_HEADER[@]}" -X POST "${BASE}/api/strategies/pipeline/run" \
  -H "Content-Type: application/json" \
  -d '{"mode":"evolve_only","evolution":{"population_limit":6,"symbol":"000001.SZ"}}')"
echo "$RUN_OUT" | _json
JOB_ID="$(echo "$RUN_OUT" | python3 -c "import sys,json; j=json.load(sys.stdin); d=j.get('data') or j; print(d.get('job_id',''))" 2>/dev/null || true)"
if [[ -z "$JOB_ID" ]]; then
  echo "未能解析 job_id（检查响应与登录态）" >&2
  exit 0
fi

echo ""
echo "== 查询任务（轮询直至非 running）=="
for _ in $(seq 1 30); do
  ST="$(curl -sS "${AUTH_HEADER[@]}" "${BASE}/api/strategies/pipeline/jobs/${JOB_ID}")"
  STATUS="$(echo "$ST" | python3 -c "import sys,json; j=json.load(sys.stdin); d=j.get('data') or j; print(d.get('status',''))" 2>/dev/null || echo "")"
  echo "status=${STATUS:-?}"
  if [[ "$STATUS" != "running" ]]; then
    echo "$ST" | _json
    break
  fi
  sleep 2
done

echo ""
echo "== admin 审批上架（需 admin 角色；若配置了 PIPELINE_APPROVE_API_KEY 则加 -H \"X-Pipeline-Approve-Key: ...\") =="
echo "curl -sS -X POST \"${BASE}/api/strategies/pipeline/jobs/${JOB_ID}/approve\" \\"
echo "  ${AUTH_HEADER[*]} -H \"Content-Type: application/json\" \\"
echo "  -d '{\"strategy_ids\":[]}'"
echo ""
echo "（strategy_ids 非空时仅上架列表与 staged 候选的交集）"
