#!/usr/bin/env python3
"""
自动化检查：目标是否实现。
- Gateway 健康与 API 可用
- MVP 数据桥：/api/dashboard, /api/stocks, /api/market/summary
- 数据管道 API：/api/market/realtime, /api/market/limitup, /api/market/fundflow
使用 TestClient 进程内检查（无需先启动服务）；若需测已启动服务可设 USE_LIVE=1。
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for d in ["gateway/src", "core/src", "data-engine/src", "data-pipeline/src"]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

def main() -> int:
    import json
    use_live = os.environ.get("USE_LIVE", "").strip().lower() in ("1", "true", "yes")
    results = []

    if use_live:
        import urllib.request
        base = os.environ.get("API_BASE", "http://127.0.0.1:8000")
        def get(path: str) -> tuple[int, dict | list]:
            try:
                req = urllib.request.Request(f"{base}{path}", headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=15) as r:
                    return r.status, json.loads(r.read().decode())
            except Exception as e:
                return 0, {"error": str(e)}
    else:
        from fastapi.testclient import TestClient
        from gateway.app import app
        client = TestClient(app)
        def get(path: str) -> tuple[int, dict | list]:
            try:
                r = client.get(path, timeout=15)
                return r.status_code, r.json() if r.content else {}
            except Exception as e:
                return 0, {"error": str(e)}

    # 1. 健康
    status, body = get("/health")
    ok = status == 200 and (isinstance(body, dict) and body.get("status") == "ok")
    results.append(("Gateway 健康 /health", ok, f"status={status}"))

    # 2. MVP 数据桥
    status, body = get("/api/dashboard")
    ok = status == 200 and isinstance(body, dict) and ("total_equity" in body or "equity_curve" in body)
    results.append(("MVP Dashboard /api/dashboard", ok, f"status={status}"))

    status, body = get("/api/stocks?limit=5")
    ok = status == 200 and isinstance(body, list)
    n = len(body) if isinstance(body, list) else 0
    results.append(("MVP Stocks /api/stocks", ok, f"status={status} len={n}"))

    status, body = get("/api/market/summary")
    ok = status == 200 and isinstance(body, dict) and "total_stocks" in body and "market" in body
    results.append(("MVP Market Summary /api/market/summary", ok, f"status={status}"))

    # 3. 数据管道 API
    status, body = get("/api/market/realtime?limit=5")
    ok = status == 200 and isinstance(body, list)
    results.append(("管道 Realtime /api/market/realtime", ok, f"status={status}"))

    status, body = get("/api/market/limitup?limit=5")
    ok = status == 200 and isinstance(body, list)
    results.append(("管道 Limitup /api/market/limitup", ok, f"status={status}"))

    status, body = get("/api/market/fundflow?limit=5")
    ok = status == 200 and isinstance(body, list)
    results.append(("管道 Fundflow /api/market/fundflow", ok, f"status={status}"))

    # 4. 数据状态（quant.duckdb）
    status, body = get("/api/data/status")
    ok = status == 200 and isinstance(body, dict)
    results.append(("Data Status /api/data/status", ok, f"status={status}"))

    status, body = get("/api/market/emotion")
    ok = status == 200 and isinstance(body, dict) and "stage" in body
    results.append(("情绪周期 /api/market/emotion", ok, f"status={status}"))

    status, body = get("/api/strategy/signals?limit=5")
    ok = status == 200 and isinstance(body, list)
    results.append(("交易信号 /api/strategy/signals", ok, f"status={status}"))

    # 打印
    print("=" * 60)
    print("目标检查结果 (Goals Check)")
    print("=" * 60)
    all_ok = True
    for name, ok, detail in results:
        all_ok = all_ok and ok
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}  ({detail})")
    print("=" * 60)
    print("全部通过" if all_ok else "存在失败项")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
