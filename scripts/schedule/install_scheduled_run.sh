#!/bin/bash
# 安装 launchd 定时任务：每周一至五 18:30 执行 run_full_cycle（锁屏/后台也会跑）。
# 用法：在 newhigh 仓库根目录执行 bash scripts/schedule/install_scheduled_run.sh
set -e
SCHEDULE_DIR="$(cd "$(dirname "$0")" && pwd)"
NEWHIGH_ROOT="$(cd "$SCHEDULE_DIR/../.." && pwd)"
WRAPPER="$SCHEDULE_DIR/run_scheduled_full_cycle.sh"
PLIST_DEST="$HOME/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist"

mkdir -p "$NEWHIGH_ROOT/logs"
touch "$NEWHIGH_ROOT/logs/launchd_stdout.log" "$NEWHIGH_ROOT/logs/launchd_stderr.log"
chmod +x "$WRAPPER"

sed -e "s|__NEWHIGH_ROOT__|$NEWHIGH_ROOT|g" \
    -e "s|__WRAPPER_SCRIPT__|$WRAPPER|g" \
    "$SCHEDULE_DIR/com.redmountain.newhigh.fullcycle.plist.template" \
    > "$PLIST_DEST"

launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"
echo "Installed: $PLIST_DEST"
echo "Schedule: Mon–Fri 18:30 (runs when logged in, including lock screen)"
echo "Logs: $NEWHIGH_ROOT/logs/full_cycle.log"
echo "Uninstall: launchctl unload $PLIST_DEST"
