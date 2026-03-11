#!/bin/bash
# 卸载定时任务
PLIST="$HOME/Library/LaunchAgents/com.redmountain.newhigh.fullcycle.plist"
launchctl unload "$PLIST" 2>/dev/null || true
[ -f "$PLIST" ] && rm -f "$PLIST" && echo "Removed $PLIST" || echo "Plist not found."
