#!/usr/bin/env bash
# 政策采集环境自检（给 OpenClaw / 人工终端用）：验证主仓路径、.venv、入口脚本，打印推荐定时配置。
# 用法：在仓库根执行  bash scripts/policy_collect_env_check.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== newhigh 政策采集 — 环境自检 ==="
echo "仓库根: $ROOT"
echo ""

ok=0
warn=0

if [[ -d "$ROOT/.venv" ]]; then
  echo "[OK] .venv 存在"
  ok=$((ok + 1))
else
  echo "[FAIL] 缺少 $ROOT/.venv — 请先: python3 -m venv .venv && pip install -r requirements.txt"
fi

for s in \
  "$ROOT/scripts/run_policy_news_collect.sh" \
  "$ROOT/scripts/run_policy_news_collect_retry.sh" \
  "$ROOT/integrations/hongshan/policy-news/news_collector.py"
do
  if [[ -f "$s" ]]; then
    echo "[OK] $s"
    ok=$((ok + 1))
  else
    echo "[FAIL] 缺少 $s"
  fi
done

if [[ -x "$ROOT/scripts/run_policy_news_collect.sh" ]]; then
  echo "[OK] run_policy_news_collect.sh 可执行"
else
  echo "[WARN] 建议: chmod +x $ROOT/scripts/run_policy_news_collect.sh $ROOT/scripts/run_policy_news_collect_retry.sh"
  warn=$((warn + 1))
fi

if [[ -f "$ROOT/.env" ]]; then
  echo "[OK] .env 存在（脚本会 source）"
else
  echo "[WARN] 无 .env — 若需 QUANT_SYSTEM_DUCKDB_PATH 等，请从 .env.example 复制"
  warn=$((warn + 1))
fi

echo ""
echo "=== 与 OpenClaw 常见误区的对照 ==="
echo "  不要用: ~/.openclaw/workspace/scripts/news_collector.py（路径可能不存在或与主仓不一致）"
echo "  请使用: $ROOT/scripts/run_policy_news_collect_retry.sh"
echo "  不要用: /usr/bin/python3 .../news_collector.py（系统 Python 常缺依赖）"
echo "  请使用: 上述 bash 包装（内部用 .venv + PYTHONPATH + .env）"
echo ""

echo "=== 推荐定时（macOS）：launchd，见 ==="
echo "  integrations/hongshan/policy-news/com.newhigh.policy-collector.plist.example"
echo "  将 REPLACE_WITH_NEWHIGH_ROOT 换为: $ROOT"
echo ""

echo "=== 可选 crontab 行（每日 08:30，日志在 logs/）==="
echo "30 8 * * * cd $ROOT && /bin/bash scripts/run_policy_news_collect_retry.sh >> logs/policy_cron.log 2>&1"
echo ""

echo "=== 试跑采集（不写 --test；直接执行即跑一次）==="
echo "  cd $ROOT && bash scripts/run_policy_news_collect_retry.sh"
echo ""

if command -v launchctl >/dev/null 2>&1; then
  uid="$(id -u)"
  if launchctl print "gui/${uid}/com.newhigh.policy-collector" >/dev/null 2>&1; then
    echo "[OK] launchd 已注册: gui/${uid}/com.newhigh.policy-collector"
  else
    echo "[INFO] 未检测到 gui/${uid}/com.newhigh.policy-collector（若未装 launchd 属正常）"
  fi
fi

echo "--- 完成 (OK 计数≈$ok, WARN≈$warn) ---"
