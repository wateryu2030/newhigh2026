#!/usr/bin/env bash
# 安装开机自启：Gateway + Next（Tunnel → http://127.0.0.1:3000）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT/config/com.newhigh.tunnel-stack.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.newhigh.tunnel-stack.plist"

chmod +x "$ROOT/scripts/run_tunnel_stack.sh"

# 将 plist 中的路径替换为当前仓库路径（若项目不在 /Users/apple/Ahope/newhigh 请运行本脚本）
sed "s|/Users/apple/Ahope/newhigh|$ROOT|g" "$PLIST_SRC" > "$PLIST_DST"

launchctl bootout "gui/$(id -u)/com.newhigh.tunnel-stack" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DST"
launchctl enable "gui/$(id -u)/com.newhigh.tunnel-stack"
echo "已安装并加载: $PLIST_DST"
echo "查看状态: launchctl print gui/$(id -u)/com.newhigh.tunnel-stack | head -20"
echo "卸载: launchctl bootout gui/$(id -u)/com.newhigh.tunnel-stack && rm -f $PLIST_DST"
