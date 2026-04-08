#!/usr/bin/env bash
# Auto-fixed by Cursor on 2026-04-03: DNS 恢复后一键补采 + 尝试拉起 launchd 用户域 Agent（非 system）。
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"

echo "======== heartbeat_recover $(date '+%Y-%m-%d %H:%M:%S') ========"
echo "ROOT=$ROOT  DOMAIN=$DOMAIN"

if curl -sf --max-time 20 "https://www.gov.cn" -o /dev/null; then
  echo "OK  HTTPS www.gov.cn 可达"
else
  echo "WARN HTTPS www.gov.cn 不可达（仍将尝试采集；若失败请检查 DNS/代理）"
fi

if [[ -x "$ROOT/scripts/run_policy_news_collect_retry.sh" ]]; then
  bash "$ROOT/scripts/run_policy_news_collect_retry.sh" || echo "WARN 政策采集脚本退出非 0，见 logs/"
else
  bash "$ROOT/scripts/run_policy_news_collect.sh" || echo "WARN 政策采集脚本退出非 0"
fi

for label in com.newhigh.news-api com.newhigh.policy-collector; do
  if launchctl print "$DOMAIN/$label" &>/dev/null; then
    echo "kickstart $label ..."
    launchctl kickstart -k "$DOMAIN/$label" 2>/dev/null || echo "WARN kickstart $label 失败（可能未加载或权限不对）"
  else
    echo "INFO 未找到 $DOMAIN/$label（若未安装 LaunchAgent 可忽略）"
  fi
done

echo "======== 建议再执行: bash scripts/heartbeat_check.sh ========"
echo "若曾错误使用 system 域安装，请改用户域: ~/Library/LaunchAgents/*.plist + bootstrap gui/\$(id -u)/..."
