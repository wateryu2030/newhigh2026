#!/usr/bin/env bash
# Auto-fixed by Cursor on 2026-04-03: 本地心跳自检；可选参数 --recover 执行 heartbeat_recover.sh。
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$ROOT/.venv/bin/python"
echo "======== newhigh heartbeat $(date '+%Y-%m-%d %H:%M:%S') ========"
echo "ROOT=$ROOT"

pass() { echo "  OK  $*"; }
fail() { echo "  FAIL $*"; }

# 1) 外网 DNS / TLS（政策源探活）
if curl -sf --max-time 15 "https://www.gov.cn" -o /dev/null; then
  pass "HTTPS www.gov.cn"
else
  fail "HTTPS www.gov.cn（常见原因：DNS、代理、防火墙）"
fi

# 2) 政策新闻 API（可选常驻）
if curl -sf --max-time 3 "http://127.0.0.1:8001/news/stats" -o /dev/null; then
  pass "policy news-api :8001 /news/stats"
else
  echo "  SKIP news-api :8001（未启动则正常；需要时见 integrations/hongshan/policy-news/README.md）"
fi

# 3) Gateway（可选）+ data-overview 新鲜度（硬检查，可 NEWHIGH_HEARTBEAT_FRESHNESS=0 跳过）
GATEWAY_UP=0
if curl -sf --max-time 3 "http://127.0.0.1:8000/health" -o /dev/null; then
  pass "Gateway :8000 /health"
  GATEWAY_UP=1
else
  echo "  SKIP Gateway :8000"
fi
if [[ "$GATEWAY_UP" == "1" ]] && [[ "${NEWHIGH_HEARTBEAT_FRESHNESS:-1}" != "0" ]] && [[ -x "$PY" ]]; then
  export PYTHONPATH="${ROOT}/data-pipeline/src:${ROOT}"
  if "$PY" "$ROOT/scripts/check_data_freshness.py" \
    --base-url "${GATEWAY_BASE_URL:-http://127.0.0.1:8000}" \
    --max-age-realtime "${NEWHIGH_HEARTBEAT_FRESHNESS_MAX_RT:-7200}" \
    --max-age-limitup "${NEWHIGH_HEARTBEAT_FRESHNESS_MAX_LU:-14400}" \
    --require-realtime; then
    pass "Gateway data-overview freshness"
  else
    fail "Gateway data-overview freshness（设 NEWHIGH_HEARTBEAT_FRESHNESS=0 跳过；或跑 bash scripts/gateway_batch_pipeline.sh）"
  fi
fi

# 4) launchd（用户域 gui/UID；勿与 system 域混淆）
UID_NUM="$(id -u)"
DOMAIN="gui/${UID_NUM}"
if launchctl list 2>/dev/null | grep -q "com.newhigh.news-api"; then
  pid="$(launchctl list 2>/dev/null | awk 'NR>1 && $3=="com.newhigh.news-api" {print $1; exit}')"
  if [[ "${pid:-}" == "-" ]]; then
    echo "  WARN com.newhigh.news-api 已加载但无运行中 PID（KeepAlive 应常驻；查 integrations/hongshan/logs/news-api-error.log）"
  else
    pass "launchd com.newhigh.news-api PID=${pid:-?}"
  fi
else
  echo "  INFO 未加载 com.newhigh.news-api（未配置 LaunchAgent 则正常）"
fi
if launchctl list 2>/dev/null | grep -q "com.newhigh.policy-collector"; then
  pass "launchd 已加载 com.newhigh.policy-collector（Calendar 任务空闲时 list 中 PID 可能为 -，属正常）"
else
  echo "  INFO 未加载 com.newhigh.policy-collector"
fi
echo "  HINT kickstart 用户域: launchctl kickstart -k ${DOMAIN}/com.newhigh.news-api"
echo "       launchctl kickstart -k ${DOMAIN}/com.newhigh.policy-collector"

# 5) DuckDB 今日政策条数（需 venv + duckdb）
if [[ -x "$PY" ]]; then
  if "$PY" -c "import duckdb" 2>/dev/null; then
    export HEARTBEAT_ROOT="$ROOT"
    out="$("$PY" <<'PY' 2>/dev/null || true
import os, sys
ROOT = os.environ.get("HEARTBEAT_ROOT", "")
sys.path.insert(0, os.path.join(ROOT, "data-pipeline", "src"))
try:
    from data_pipeline.storage.duckdb_manager import get_db_path
    import duckdb
    p = get_db_path()
    if not os.path.isfile(p):
        print("SKIP no db")
        sys.exit(0)
    con = duckdb.connect(p, read_only=True)
    r = con.execute(
        """
        SELECT COUNT(*) FROM news_items
        WHERE symbol = '__POLICY__' AND CAST(ts AS DATE) = CURRENT_DATE
        """
    ).fetchone()
    print("policy_rows_today", r[0] if r else 0)
    con.close()
except Exception as e:
    print("ERR", e)
PY
)"
    echo "  DB  $out"
  else
    echo "  SKIP DuckDB 统计（未安装 duckdb 包）"
  fi
else
  echo "  SKIP DuckDB 统计（无 .venv/bin/python）"
fi

echo "--- 手动补采（DNS 恢复后）---"
echo "  bash $ROOT/scripts/run_policy_news_collect_retry.sh"
echo "  或 bash $ROOT/scripts/run_policy_news_collect.sh"
echo "--- 一键恢复 ---"
echo "  bash $ROOT/scripts/heartbeat_recover.sh"
echo "======== end heartbeat ========"
if [[ "${1:-}" == "--recover" ]]; then
  bash "$ROOT/scripts/heartbeat_recover.sh"
fi
