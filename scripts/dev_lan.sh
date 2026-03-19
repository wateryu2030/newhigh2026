#!/usr/bin/env bash
# 局域网调试：打印本机 IP 与推荐启动命令
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IP=""
if command -v ipconfig &>/dev/null; then
  IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)
fi
if [ -z "$IP" ] && command -v hostname &>/dev/null; then
  IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi
echo "========== newhigh 局域网访问 =========="
echo "本机 IP（示例）: ${IP:-请手动在 系统设置→网络 查看}"
echo ""
echo "1) Gateway（须 0.0.0.0）:"
echo "   cd $ROOT && source .venv/bin/activate && uvicorn gateway.app:app --host 0.0.0.0 --port 8000"
echo ""
echo "2) 前端:"
echo "   cd $ROOT/frontend && npx next dev -H 0.0.0.0 -p 3000"
echo ""
echo "3) 手机打开: http://${IP:-你的IP}:3000"
echo "   再在网页「设置」填写 Gateway: http://${IP:-你的IP}:8000"
echo "========================================"
