#!/usr/bin/env bash
# 打开本机 OpenClaw：加载 .env（含百炼 API Key）并启动 Gateway，可选打开前端
# 使用：bash scripts/open_openclaw.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# 加载 .env（含 BAILIAN_API_KEY / DASHSCOPE_API_KEY）
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env" 2>/dev/null || true
  set +a
  echo "[OpenClaw] 已加载 .env（百炼 API Key 已就绪）"
else
  echo "[OpenClaw] 未找到 .env，请复制 .env.example 并配置 BAILIAN_API_KEY"
fi

# 检查 Gateway 是否已在运行
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null | grep -q 200; then
  echo "[OpenClaw] Gateway 已在运行 (http://127.0.0.1:8000)"
else
  echo "[OpenClaw] 正在启动 Gateway..."
  (source "$ROOT/.venv/bin/activate" 2>/dev/null; uvicorn gateway.app:app --host 127.0.0.1 --port 8000) &
  sleep 3
  if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null | grep -q 200; then
    echo "[OpenClaw] Gateway 已启动 (http://127.0.0.1:8000)"
  else
    echo "[OpenClaw] Gateway 启动失败，请手动执行: uvicorn gateway.app:app --host 127.0.0.1 --port 8000"
  fi
fi

echo ""
echo "OpenClaw 已就绪。百炼 API Key 已从 .env 加载。"
echo "  - API 文档: http://127.0.0.1:8000/docs"
echo "  - 系统监控（进化任务 / Skill 统计）: http://localhost:3000/system-monitor（需先 cd frontend && npm run dev）"
echo "  - 进化循环: bash scripts/cursor_evolution_cycle.sh"
