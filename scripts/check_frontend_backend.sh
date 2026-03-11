#!/usr/bin/env bash
# 前后端联调检查：Gateway 与前端调用的 API 是否一一对应、返回 200 且结构可用
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BASE="${API_BASE:-http://127.0.0.1:8000}"
PASS=0
FAIL=0
report() { echo "[CHECK] $1"; }
ok()    { report "PASS: $1"; PASS=$((PASS+1)); }
fail()  { report "FAIL: $1"; FAIL=$((FAIL+1)); }

echo "========== 前后端服务配合检查 =========="
echo "Gateway: $BASE (可通过 API_BASE 覆盖)"
echo ""

# 1. Gateway 存活
report "Gateway 存活..."
if ! curl -s -o /dev/null -w "%{http_code}" "$BASE/health" 2>/dev/null | grep -q 200; then
  fail "Gateway 未响应 (请先启动: uvicorn gateway.app:app --host 127.0.0.1 --port 8000)"
  echo ""
  echo "PASS: $PASS  FAIL: $FAIL"
  exit 1
fi
ok "Gateway /health 200"

# 2. 前端调用的 GET 接口（与 frontend/src/api/client.ts 对应）
check_get() {
  local path="$1"
  local name="$2"
  local code
  code=$(curl -s -o /tmp/check_resp.json -w "%{http_code}" "$BASE/api$path" 2>/dev/null || echo "000")
  if [ "$code" = "200" ]; then
    if python3 -c "import json; json.load(open('/tmp/check_resp.json'))" 2>/dev/null; then
      ok "GET $path (JSON 有效)"
    else
      fail "GET $path (非 JSON)"
    fi
  else
    fail "GET $path (HTTP $code)"
  fi
}

report "前端使用的 GET 接口..."
check_get "/dashboard" "dashboard"
check_get "/data/status" "data/status"
check_get "/market/summary" "market/summary"
check_get "/stocks?limit=10" "stocks"
check_get "/strategies" "strategies"
check_get "/strategies/market?limit=5" "strategies/market"
check_get "/portfolio/weights" "portfolio/weights"
check_get "/risk/status" "risk/status"
check_get "/market/klines?symbol=600519.SH&interval=1d" "market/klines"
check_get "/market/ashare/stocks" "market/ashare/stocks"
check_get "/news?limit=5" "news"
check_get "/trades" "trades"
check_get "/evolution" "evolution"
check_get "/alpha-lab" "alpha-lab"
check_get "/positions" "positions"
check_get "/market/emotion" "market/emotion"
check_get "/market/hotmoney?limit=5" "market/hotmoney"
check_get "/market/main-themes?limit=5" "market/main-themes"
check_get "/strategy/signals?limit=5" "strategy/signals"
check_get "/market/sniper-candidates?limit=5" "market/sniper-candidates"
check_get "/system/status?limit=5" "system/status"
check_get "/ai/decision" "ai/decision"
check_get "/backtest/result" "backtest/result"
check_get "/execution/equity_curve?limit=10" "execution/equity_curve"
check_get "/execution/mode" "execution/mode"
check_get "/simulated/orders?limit=5" "simulated/orders"
check_get "/simulated/positions?limit=5" "simulated/positions"

# 3. Dashboard 响应结构（前端依赖字段）
report "Dashboard 结构 (total_equity, daily_return_pct, equity_curve)..."
if curl -s "$BASE/api/dashboard" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
need = ['total_equity', 'daily_return_pct', 'equity_curve']
miss = [k for k in need if k not in d]
sys.exit(0 if not miss else 1)
" 2>/dev/null; then
  ok "Dashboard 含必需字段"
else
  fail "Dashboard 缺少前端依赖字段"
fi

# 4. Portfolio 结构（weights, capital）
report "Portfolio 结构 (weights, capital)..."
if curl -s "$BASE/api/portfolio/weights" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
need = ['weights', 'capital']
miss = [k for k in need if k not in d]
sys.exit(0 if not miss else 1)
" 2>/dev/null; then
  ok "Portfolio 含 weights/capital"
else
  fail "Portfolio 缺少 weights 或 capital"
fi

# 5. DataStatus 结构（ok, stocks, daily_bars）
report "DataStatus 结构 (ok, stocks, daily_bars)..."
if curl -s "$BASE/api/data/status" 2>/dev/null | python3 -c "
import json, sys
d = json.load(sys.stdin)
need = ['ok', 'stocks', 'daily_bars']
miss = [k for k in need if k not in d]
sys.exit(0 if not miss else 1)
" 2>/dev/null; then
  ok "DataStatus 含必需字段"
else
  fail "DataStatus 缺少前端依赖字段"
fi

# 6. POST ensure-stocks（前端股票页空数据时调用）
report "POST /api/data/ensure-stocks..."
code=$(curl -s -o /tmp/check_post.json -w "%{http_code}" -X POST "$BASE/api/data/ensure-stocks" 2>/dev/null || echo "000")
if [ "$code" = "200" ]; then
  if python3 -c "import json; d=json.load(open('/tmp/check_post.json')); exit(0 if 'ok' in d else 1)" 2>/dev/null; then
    ok "POST data/ensure-stocks 返回 ok"
  else
    fail "POST data/ensure-stocks 响应无 ok"
  fi
else
  fail "POST data/ensure-stocks HTTP $code"
fi

# 7. 前端构建与路由存在性
report "前端页面与 API 客户端..."
[ -f "$ROOT/frontend/src/app/page.tsx" ] && ok "Dashboard 页" || fail "Dashboard 页"
[ -f "$ROOT/frontend/src/app/stocks/page.tsx" ] && ok "Stocks 页" || fail "Stocks 页"
[ -f "$ROOT/frontend/src/app/trade/page.tsx" ] && ok "Trade 页" || fail "Trade 页"
[ -f "$ROOT/frontend/src/app/portfolio/page.tsx" ] && ok "Portfolio 页" || fail "Portfolio 页"
[ -f "$ROOT/frontend/src/api/client.ts" ] && ok "api/client.ts" || fail "api/client.ts"

echo ""
echo "========== 汇总 =========="
echo "PASS: $PASS  FAIL: $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "存在失败项，请检查 Gateway 与 frontend 对接。"
  exit 1
fi
echo "前后端服务配合检查通过。"
