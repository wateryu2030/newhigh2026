#!/usr/bin/env bash
# 启动 Gateway + 前端，绑定 0.0.0.0，供局域网 / 端口转发后的外网访问
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [ -f ".venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source .venv/bin/activate
fi

for p in 8000 3000; do
  PIDS=$(lsof -ti ":$p" 2>/dev/null || true)
  [ -n "$PIDS" ] && kill $PIDS 2>/dev/null || true
done
sleep 1

echo "[1/2] Gateway http://0.0.0.0:8000"
uvicorn gateway.app:app --host 0.0.0.0 --port 8000 &
GWPID=$!

sleep 2
echo "[2/2] Frontend http://0.0.0.0:3000"
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
(cd "$ROOT/frontend" && npx next dev -H 0.0.0.0 -p 3000) &
NPID=$!

IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "本机IP")
echo ""
echo "========== 已启动（全网卡监听）=========="
echo "  本机:   http://127.0.0.1:3000  | API http://127.0.0.1:8000"
echo "  局域网: http://${IP}:3000      | API http://${IP}:8000"
echo "  外网:   须在路由器将 3000/8000 转发到本机 ${IP}，或见 docs/NEWHIGH_COM_CLOUDFLARE.md（Tunnel）"
echo "  手机访问请在网页「设置」填写 Gateway: http://${IP}:8000"
echo "  停止: kill $GWPID $NPID"
echo "========================================="

wait
