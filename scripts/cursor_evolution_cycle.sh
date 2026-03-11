#!/usr/bin/env bash
# Cursor + OpenClaw 进化开发循环：触发进化 → 轮询状态 → 代码检查 → 前后端验证 → 刷新系统状态
# 使用：bash scripts/cursor_evolution_cycle.sh
# 前置：Gateway 已启动（http://127.0.0.1:8000）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE="${API_BASE:-http://127.0.0.1:8000}"

echo "=== Cursor + OpenClaw 进化开发循环 ==="

# 1. 触发 OpenClaw 进化任务
echo "1. 触发 OpenClaw 策略进化任务..."
RESP=$(curl -s -X POST "$BASE/api/evolution/trigger?task_type=strategy_generation&population_limit=10" || true)
TASK_ID=$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('task_id',''))" 2>/dev/null <<< "$RESP" || echo "")
if [ -z "$TASK_ID" ]; then
  echo "  未能获取 task_id，响应: $RESP"
  echo "  请确认 Gateway 已启动: $BASE"
  exit 1
fi
echo "  进化任务 ID: $TASK_ID"

# 2. 轮询任务状态
echo "2. 等待任务完成（轮询）..."
MAX_WAIT=300
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  ST=$(curl -s "$BASE/api/evolution/status/$TASK_ID" 2>/dev/null || echo "{}")
  STATUS=$(python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('status','PENDING'))" 2>/dev/null <<< "$ST" || echo "PENDING")
  if [ "$STATUS" = "SUCCESS" ]; then
    echo "  进化任务完成"
    break
  elif [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "FAILURE" ]; then
    echo "  进化任务失败"
    echo "$ST" | python3 -m json.tool 2>/dev/null || echo "$ST"
    exit 1
  fi
  echo "  任务状态: $STATUS (${ELAPSED}s)"
  sleep 10
  ELAPSED=$((ELAPSED + 10))
done
if [ $ELAPSED -ge $MAX_WAIT ]; then
  echo "  超时未完成"
  exit 1
fi

# 3. 代码检查与格式化（可选，存在则执行）
echo "3. 代码检查..."
if command -v black >/dev/null 2>&1; then
  black . --quiet 2>/dev/null || true
fi
if command -v isort >/dev/null 2>&1; then
  isort . --quiet 2>/dev/null || true
fi

# 4. 前后端联调验证
echo "4. 前后端联调检查..."
if [ -f "$ROOT/scripts/check_frontend_backend.sh" ]; then
  bash scripts/check_frontend_backend.sh || true
else
  echo "  跳过（无 check_frontend_backend.sh）"
fi

# 5. 刷新系统状态（可选）
echo "5. 刷新系统状态..."
if [ -d "$ROOT/system_core" ]; then
  (cd "$ROOT" && python -m system_core.system_runner --once 2>/dev/null) || true
fi

echo "=== 进化开发循环完成 ==="
echo "可访问 http://localhost:3000/system-monitor 查看 OpenClaw 进化任务与 Skill 统计"
