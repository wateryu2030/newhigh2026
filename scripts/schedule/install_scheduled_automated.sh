#!/bin/bash
# 安装 launchd 定时任务：每周一至五 18:30 执行 run_automated（Tushare 拉取 + 全周期）。
# 用法：在 newhigh 仓库根目录执行 bash scripts/schedule/install_scheduled_automated.sh
set -e
SCHEDULE_DIR="$(cd "$(dirname "$0")" && pwd)"
NEWHIGH_ROOT="$(cd "$SCHEDULE_DIR/../.." && pwd)"
WRAPPER="$NEWHIGH_ROOT/scripts/run_automated.sh"
PLIST_DEST="$HOME/Library/LaunchAgents/com.redmountain.newhigh.automated.plist"

mkdir -p "$NEWHIGH_ROOT/logs"
touch "$NEWHIGH_ROOT/logs/launchd_stdout.log" "$NEWHIGH_ROOT/logs/launchd_stderr.log"
chmod +x "$WRAPPER"

sed -e "s|__NEWHIGH_ROOT__|$NEWHIGH_ROOT|g" \
    -e "s|__WRAPPER_SCRIPT__|$WRAPPER|g" \
    "$SCHEDULE_DIR/com.redmountain.newhigh.automated.plist.template" \
    > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "Installed: $PLIST_DEST"
echo "Schedule: Mon–Fri 18:30 (Tushare + full cycle, log: logs/automated.log)"
echo "Uninstall: launchctl unload $PLIST_DEST"
