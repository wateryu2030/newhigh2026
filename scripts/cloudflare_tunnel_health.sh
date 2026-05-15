#!/usr/bin/env bash
# 本机诊断 Cloudflare Tunnel + newhigh 栈，辅助排查 Error 1033 / 多子域并行。
# 用法：仓库根执行  bash scripts/cloudflare_tunnel_health.sh
# 可选：XIAOAN_LOCAL_PORT=8765  小安智服本机监听端口（仅做 curl 探活）

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CF_LOG_CANDIDATES=(/tmp/cloudflared.log /opt/homebrew/var/log/cloudflared.log)
XIAOAN_LOCAL_PORT="${XIAOAN_LOCAL_PORT:-}"
HTMA_HOST="${HTMA_HOST:-htma.newhigh.com.cn}"
XIAOAN_HOST="${XIAOAN_HOST:-xiaoan.newhigh.com.cn}"

echo "仓库: ${ROOT}"
echo "== cloudflared 进程 =="
if pgrep -x cloudflared >/dev/null 2>&1; then
  pgrep -x cloudflared | while read -r p; do
    echo "  pid=$p (argv 见 ps，勿泄露 --token)"
  done
else
  echo "  [失败] 未检测到 cloudflared → 公网常报 Error 1033。请启动："
  echo '    brew services start cloudflared   # 或 launchctl kickstart -k gui/$(id -u)/homebrew.mxcl.cloudflared'
fi

echo ""
echo "== tunnel 栈（Gateway+Next）LaunchAgent =="
if launchctl print "gui/$(id -u)/com.newhigh.tunnel-stack" >/dev/null 2>&1; then
  launchctl print "gui/$(id -u)/com.newhigh.tunnel-stack" 2>/dev/null | grep -E 'state =|program =' || true
else
  echo "  [提示] 未安装 com.newhigh.tunnel-stack（仅影响本机 :3000，与 cloudflared 独立）"
  echo "    bash scripts/install_tunnel_stack_launchagent.sh"
fi

echo ""
echo "== 本机源站（Tunnel 应指向 Next :3000）=="
code="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 -H "Host: ${HTMA_HOST}" "http://127.0.0.1:3000/" 2>/dev/null || echo fail)"
echo "  curl -H Host:${HTMA_HOST} http://127.0.0.1:3000/ → HTTP ${code}"
if [[ "$code" != "200" ]]; then
  echo "  [失败] 先修复本机 Next/Gateway：bash scripts/restart_gateway_frontend.sh"
fi

if [[ -n "${XIAOAN_LOCAL_PORT}" ]]; then
  xcode="$(curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 2 -H "Host: ${XIAOAN_HOST}" "http://127.0.0.1:${XIAOAN_LOCAL_PORT}/" 2>/dev/null || echo fail)"
  echo "  curl -H Host:${XIAOAN_HOST} http://127.0.0.1:${XIAOAN_LOCAL_PORT}/ → HTTP ${xcode}"
fi

echo ""
echo "== cloudflared 最近一次「远程 ingress」（须含公网主机名）=="
found=""
for f in "${CF_LOG_CANDIDATES[@]}"; do
  if [[ -f "$f" ]] && grep -q "Updated to new configuration" "$f" 2>/dev/null; then
    echo "  日志: $f"
    grep "Updated to new configuration" "$f" | tail -1 | sed 's/^/  /'
    found=1
    tid="$(grep -m1 'Starting tunnel tunnelID=' "$f" 2>/dev/null | sed -n 's/.*tunnelID=\([^ ]*\).*/\1/p' || true)"
    if [[ -n "${tid}" ]]; then
      echo "  当前连接器 tunnelID=${tid}"
    fi
    break
  fi
done
if [[ -z "${found}" ]]; then
  echo "  [提示] 未在 ${CF_LOG_CANDIDATES[*]} 找到 ingress 行；若刚启动请稍等或检查 cloudflared 日志路径。"
fi

echo ""
echo "== Error 1033 / 多子域并行（须在 Cloudflare Zero Trust 控制台配置）=="
echo "  1033 表示：DNS 指向的隧道当前没有健康连接器，或主机名未绑在该隧道上。"
echo "  在 **同一隧道**（与本机 cloudflared --token 一致）→ Public Hostname 增加："
echo "    1) ${HTMA_HOST}  → http://127.0.0.1:3000   （newhigh；须跑 com.newhigh.tunnel-stack 或等价）"
if [[ -n "${XIAOAN_LOCAL_PORT}" ]]; then
  echo "    2) ${XIAOAN_HOST} → http://127.0.0.1:${XIAOAN_LOCAL_PORT} （小安智服，与本项目并行）"
else
  echo "    2) ${XIAOAN_HOST} → http://127.0.0.1:<小安端口>  （设置环境变量 XIAOAN_LOCAL_PORT 后重跑本脚本可探活）"
fi
echo "  保存后 cloudflared 会自动拉取新配置，无需改 token。"
echo "  参考：config/cloudflare/config.example.yml 、 docs/NEWHIGH_COM_CLOUDFLARE.md"

echo ""
echo "== 可选：重启本机 cloudflared（拉配置 / 恢复连接）=="
echo '  launchctl kickstart -k gui/$(id -u)/homebrew.mxcl.cloudflared 2>/dev/null || brew services restart cloudflared'
