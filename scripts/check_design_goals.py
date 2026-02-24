#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设计目标自检：数据同步、策略列表、股票选择、回测接口
"""
import os
import sys
import urllib.request
import json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE)
if BASE not in sys.path:
    sys.path.insert(0, BASE)
BASE_URL = "http://127.0.0.1:5050"


def check_data_sync():
    """检查数据同步情况（DuckDB）"""
    print("【1】数据同步情况")
    try:
        from database.duckdb_backend import get_db_backend
        db_path = os.path.join(BASE, "data", "quant.duckdb")
        if not os.path.exists(db_path):
            print("   ❌ 数据库文件不存在: data/quant.duckdb")
            return False
        db = get_db_backend()
        stocks = db.get_stocks()
        print(f"   ✅ 数据库: {len(stocks)} 只股票")
        for ob, sym, name in (stocks or [])[:5]:
            import duckdb
            conn = duckdb.connect(db_path, read_only=True)
            cnt = conn.execute("SELECT COUNT(*) FROM daily_bars WHERE order_book_id = ?", [ob]).fetchone()[0]
            conn.close()
            print(f"      - {ob} ({sym}): {cnt} 条日线")
        if len(stocks or []) > 5:
            print(f"      ... 共 {len(stocks)} 只")
        return True
    except Exception as e:
        print(f"   ❌ {e}")
        return False


def check_web_api():
    """检查 Web 接口（需先启动 web_platform.py）"""
    print("\n【2】Web 平台接口（需已启动: python web_platform.py）")
    ok = True
    try:
        with urllib.request.urlopen(BASE_URL + "/", timeout=3) as r:
            if r.status != 200:
                print(f"   ❌ 首页状态码: {r.status}")
                ok = False
            else:
                print("   ✅ 首页可访问")
    except Exception as e:
        print(f"   ⚠️  首页: {e}（请先运行 python web_platform.py）")
        return False

    try:
        with urllib.request.urlopen(BASE_URL + "/api/strategies", timeout=3) as r:
            data = json.loads(r.read().decode())
            strategies = data.get("strategies", [])
            print(f"   ✅ 策略下拉: {len(strategies)} 个策略")
            for s in strategies[:3]:
                name = s.get("name", s.get("file", s)) if isinstance(s, dict) else s
                print(f"      - {name}")
            if len(strategies) > 3:
                print(f"      ... 等共 {len(strategies)} 个")
    except Exception as e:
        print(f"   ❌ /api/strategies: {e}")
        ok = False

    try:
        with urllib.request.urlopen(BASE_URL + "/api/stocks", timeout=3) as r:
            data = json.loads(r.read().decode())
            stocks = data.get("stocks", [])
            print(f"   ✅ 股票下拉: {len(stocks)} 只股票")
            for s in stocks:
                print(f"      - {s.get('order_book_id')} ({s.get('symbol')})")
    except Exception as e:
        print(f"   ❌ /api/stocks: {e}")
        ok = False

    return ok


def check_backtest_cli():
    """检查命令行回测（数据库数据源）"""
    print("\n【3】回测机制（数据库数据源）")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "run_backtest_db.py", "strategies/universal_ma_strategy.py", "2024-01-01", "2024-01-10"],
            capture_output=True, text=True, timeout=60, cwd=BASE,
            env={**os.environ, "STOCK_CODE": "600745.XSHG"}
        )
        if result.returncode == 0:
            print("   ✅ run_backtest_db.py 回测成功")
        else:
            print(f"   ❌ 回测退出码: {result.returncode}")
            if result.stderr:
                print("   错误摘要:", result.stderr[:300])
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ {e}")
        return False


def main():
    print("=" * 50)
    print("设计目标自检")
    print("=" * 50)
    r1 = check_data_sync()
    r2 = check_web_api()
    r3 = check_backtest_cli()
    print("\n" + "=" * 50)
    print("汇总:")
    print("  数据同步: " + ("✅ 通过" if r1 else "❌ 未通过"))
    print("  Web 策略/股票选择: " + ("✅ 通过" if r2 else "❌ 未通过（请先启动 web_platform.py）"))
    print("  回测机制: " + ("✅ 通过" if r3 else "❌ 未通过"))
    print("=" * 50)
    if r1 and r2 and r3:
        print("建议: 在浏览器打开 http://127.0.0.1:5050 进行完整操作测试。")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
