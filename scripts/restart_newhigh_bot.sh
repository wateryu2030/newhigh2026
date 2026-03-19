#!/usr/bin/env bash
# 重启飞书 newhigh 机器人后端（OpenClaw Gateway）
# LaunchAgent: ai.openclaw.gateway，端口 18789，配置在 ~/.openclaw/openclaw.json
set -e
echo "[$(date -Iseconds)] Restarting OpenClaw Gateway (newhigh bot)..."
launchctl stop ai.openclaw.gateway 2>/dev/null || true
sleep 2
launchctl start ai.openclaw.gateway
sleep 2
if launchctl list ai.openclaw.gateway | grep -q '"PID" = [0-9]'; then
  echo "[$(date -Iseconds)] Gateway started."
  if curl -sf -o /dev/null "http://127.0.0.1:18789/" 2>/dev/null; then
    echo "Health: http://127.0.0.1:18789/ -> 200 OK"
  else
    echo "Warn: port 18789 not responding yet (may need a few more seconds)."
  fi
else
  echo "Error: ai.openclaw.gateway may have failed to start. Check: launchctl list ai.openclaw.gateway"
  exit 1
fi
