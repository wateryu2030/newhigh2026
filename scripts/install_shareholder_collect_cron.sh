#!/usr/bin/env bash
# 安装十大股东定时采集（LaunchAgent 每日 2:00）
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLIST_SRC="$ROOT/config/com.newhigh.shareholder-collect.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.newhigh.shareholder-collect.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cp "$PLIST_SRC" "$PLIST_DEST"
launchctl load "$PLIST_DEST"
echo "已安装: $PLIST_DEST"
echo "每日 2:00 执行，日志: $ROOT/logs/shareholder_collect.log"
