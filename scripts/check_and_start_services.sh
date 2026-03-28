#!/usr/bin/env bash
# 检查 Gateway(8000) + Next(3000)；失败则调用 restart_gateway_frontend.sh。
# 用法：bash scripts/check_and_start_services.sh
# 可选：NEWHIGH_FRONTEND_PROD=1 与重启脚本一致（生产 build+start）
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:${PATH:-}"

gw="http://127.0.0.1:8000/health"
nx="http://127.0.0.1:3000/"
sent="http://127.0.0.1:8000/api/market/sentiment-7d"

code() {
  curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 8 "$1" || echo "000"
}

# 情绪接口可能拉东财/AkShare，8s 不够则误判失败
code_slow() {
  curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 90 "$1" || echo "000"
}

check_all() {
  CG=$(code "$gw")
  CN=$(code "$nx")
  echo "[check] Gateway $gw -> HTTP $CG"
  echo "[check] Next     $nx -> HTTP $CN"
  if [[ "$CG" == "200" && "$CN" == "200" ]]; then
    return 0
  fi
  return 1
}

if check_all; then
  echo "[check] 服务正常，跳过重启。"
else
  echo "[check] 异常，执行重启…"
  # 与手动部署一致：生产可 export NEWHIGH_FRONTEND_PROD=1
  bash "$ROOT/scripts/restart_gateway_frontend.sh"
  sleep 3
  if ! check_all; then
    echo "[check] 重启后仍异常。Gateway 日志: $ROOT/logs/gateway.out" >&2
    echo "[check] 前端日志: $ROOT/logs/frontend.out" >&2
    exit 1
  fi
  echo "[check] 重启后已恢复。"
fi

CS=$(code_slow "$sent")
echo "[check] sentiment-7d -> HTTP $CS"
if [[ "$CS" != "200" ]]; then
  echo "[check] 警告: 7维情绪接口非 200，请查 Gateway 与 QUANT_SYSTEM_DUCKDB_PATH" >&2
  exit 1
fi

NNEWS=$(code "http://127.0.0.1:3000/api/news?limit=1")
echo "[check] Next→/api/news -> HTTP $NNEWS"
if [[ "$NNEWS" != "200" ]]; then
  echo "[check] 警告: 经 Next 反代的新闻接口非 200（公网 /news 依赖）；请查 API_PROXY_TARGET、Gateway 与 logs/frontend.out" >&2
  exit 1
fi

NCOL=$(code "http://127.0.0.1:3000/api/news/collector?limit=1")
echo "[check] Next→/api/news/collector -> HTTP $NCOL"
if [[ "$NCOL" != "200" ]]; then
  echo "[check] 警告: 政策采集接口非 200（主站 /news 第二 Tab）" >&2
  exit 1
fi

echo "[check] 全部通过。"
