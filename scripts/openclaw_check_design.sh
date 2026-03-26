#!/usr/bin/env bash
# OpenClaw design-goal validation: OPENCLAW_AUTONOMOUS_DEV.yaml + FRONTEND_SYSTEM_SPEC.md
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate 2>/dev/null || true

PASS=0
FAIL=0
report() { echo "[CHECK] $1"; }
ok()    { report "PASS: $1"; PASS=$((PASS+1)); }
fail()  { report "FAIL: $1"; FAIL=$((FAIL+1)); }

echo "========== OpenClaw Design Goal Check =========="

# --- OPENCLAW validation: must_compile ---
report "must_compile (backend: Python imports)..."
if python -c "
from core import OHLCV, Signal
from data_engine import fetch_klines
from feature_engine import build_feature_matrix
from backtest_engine import run_backtest, compute_metrics
from strategy_engine import trend_following_signals
from portfolio_engine import equal_weight_weights
from risk_engine import should_disable_strategy_drawdown
from execution_engine import place_order
from ai_lab import generate_strategy
from evolution_engine import StrategyPool, alpha_score
from ai_fund_manager import allocate_capital
from scheduler import connect_pipeline
from gateway.app import app
print('ok')
" 2>/dev/null | grep -q ok; then
  ok "Backend compiles (all modules import)"
else
  fail "Backend compiles"
fi

report "must_compile (frontend: Next.js build)..."
FB=$(cd frontend && npm run build 2>&1)
if echo "$FB" | grep -q "Compiled successfully\|Generating static pages\|Route (app)"; then
  ok "Frontend builds (Next.js)"
else
  echo "$FB" | tail -15
  fail "Frontend builds"
fi

# --- OPENCLAW validation: must_pass_tests ---
report "must_pass_tests (backend)..."
set +e
OUT=$(bash scripts/run_tests.sh 2>&1)
R=$?
set -e
if [ $R -eq 0 ] && echo "$OUT" | tail -5 | grep -q "passed\|All tests passed"; then
  ok "Backend tests pass"
else
  echo "$OUT" | tail -20
  fail "Backend tests (run: bash scripts/run_tests.sh)"
fi

# --- FRONTEND_SYSTEM_SPEC: pages ---
report "Frontend pages (FRONTEND_SYSTEM_SPEC)..."
[ -f "$ROOT/frontend/src/app/page.tsx" ] && ok "Page: Dashboard (/)"
for p in market strategies alpha-lab evolution portfolio risk trade reports settings; do
  [ -f "$ROOT/frontend/src/app/$p/page.tsx" ] && ok "Page: $p" || fail "Page: $p"
done

# --- FRONTEND_SYSTEM_SPEC: API endpoints (gateway) ---
report "Gateway API endpoints (FRONTEND_SYSTEM_SPEC)..."
EP="$ROOT/gateway/src/gateway/endpoints.py"
grep -q "def get_dashboard" "$EP" && ok "API: /api/dashboard" || fail "API: /api/dashboard"
grep -q "def get_evolution"  "$EP" && ok "API: /api/evolution"  || fail "API: /api/evolution"
grep -q "def get_trades"     "$EP" && ok "API: /api/trades"     || fail "API: /api/trades"
grep -q "def get_alpha_lab"  "$EP" && ok "API: /api/alpha-lab"  || fail "API: /api/alpha-lab"
grep -q "def get_alpha_lab_drill" "$EP" && ok "API: /api/alpha-lab/drill" || fail "API: /api/alpha-lab/drill"
grep -q "list_strategies\|/strategies" "$EP" && ok "API: /api/strategies" || fail "API: /api/strategies"
grep -q "get_portfolio_weights\|/portfolio" "$EP" && ok "API: /api/portfolio" || fail "API: /api/portfolio"
grep -q "risk_status\|/risk" "$EP" && ok "API: /api/risk" || fail "API: /api/risk"
grep -q "get_klines\|/market" "$EP" && ok "API: /api/market" || fail "API: /api/market"

# --- FRONTEND_SYSTEM_SPEC: stack & structure ---
report "Frontend stack (Next.js, Tailwind, Zustand, Recharts)..."
grep -q "next" frontend/package.json && ok "Next.js" || fail "Next.js"
grep -q "tailwindcss" frontend/package.json && ok "Tailwind" || fail "Tailwind"
grep -q "zustand" frontend/package.json && ok "Zustand" || fail "Zustand"
grep -q "recharts" frontend/package.json && ok "Recharts" || fail "Recharts"
[ -d frontend/src/app ] && ok "App Router (src/app)" || fail "App Router"
[ -d frontend/src/components ] && ok "components/" || fail "components/"
[ -d frontend/src/api ] && ok "api/" || fail "api/"
[ -d frontend/src/store ] && ok "store/" || fail "store/"

# --- Live API check (if gateway is up) ---
report "Live API (gateway :8000)..."
if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/health 2>/dev/null | grep -q 200; then
  ok "Gateway /health 200"
  for u in /api/dashboard /api/evolution /api/alpha-lab /api/trades; do
    if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000$u" 2>/dev/null | grep -q 200; then
      ok "GET $u 200"
    else
      fail "GET $u"
    fi
  done
else
  report "Skip live API (start gateway: uvicorn gateway.app:app --port 8000)"
fi

echo "========== Summary =========="
echo "PASS: $PASS  FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then exit 1; fi
echo "Design goals met."
