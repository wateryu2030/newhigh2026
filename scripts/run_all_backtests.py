#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 002701、600598、300212 等标的，批量测试所有策略是否能正常执行。
用于验证项目能满足多数 A 股的分析与回测需求。
"""
import os
import sys
import subprocess
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


# 测试标的（代码.交易所）
TEST_STOCKS = ["002701.XSHE", "600598.XSHG", "300212.XSHE"]
# 回测区间
START_DATE = "2025-02-20"
END_DATE = "2026-02-20"


def get_strategies():
    """获取需要测试的策略列表（排除 __init__、utils、akshare 专用）"""
    exclude = {"__init__.py", "utils.py", "simple_akshare_strategy.py", "buy_and_hold_akshare.py"}
    strategies = []
    for path in sorted(glob.glob(os.path.join(ROOT, "strategies", "*.py"))):
        name = os.path.basename(path)
        if name in exclude or name.startswith(".tmp_"):
            continue
        strategies.append((name, path))
    return strategies


def ensure_data_and_run(strategy_name, strategy_path, stock_code, start_date, end_date):
    """补齐策略数据（若有）并执行回测，返回 (成功, 错误信息)"""
    try:
        from database.auto_fix_strategy_data import ensure_data_files
        ensure_data_files(strategy_path, stock_code)
    except Exception as e:
        pass  # 忽略补齐失败，继续回测

    # 非 universal 策略需要注入股票代码（生成临时策略）
    temp_path = None
    if "universal" not in strategy_name.lower():
        try:
            from web_platform_helper import inject_stock_code_to_strategy
            temp_path = inject_stock_code_to_strategy(strategy_path, stock_code)
            if temp_path != strategy_path:
                strategy_path = temp_path
        except Exception:
            pass

    env = os.environ.copy()
    env["STOCK_CODE"] = stock_code
    env["PYTHONPATH"] = os.pathsep.join(sys.path)

    cmd = [
        sys.executable,
        os.path.join(ROOT, "run_backtest_db.py"),
        strategy_path,
        start_date,
        end_date,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if temp_path and temp_path != strategy_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if result.returncode == 0:
            return True, None
        err = (result.stderr or result.stdout or "")[-800:]
        return False, err
    except subprocess.TimeoutExpired:
        return False, "回测超时(120s)"
    except Exception as e:
        return False, str(e)


def main():
    stocks = sys.argv[1:4] if len(sys.argv) >= 4 else TEST_STOCKS
    if len(sys.argv) >= 6:
        start_date = sys.argv[4]
        end_date = sys.argv[5]
    else:
        start_date = START_DATE
        end_date = END_DATE

    strategies = get_strategies()
    print(f"标的: {stocks}")
    print(f"区间: {start_date} ~ {end_date}")
    print(f"策略数: {len(strategies)}")
    print("-" * 60)

    results = []
    for name, path in strategies:
        for stock in stocks:
            ok, err = ensure_data_and_run(name, path, stock, start_date, end_date)
            results.append((name, stock, ok, err))
            status = "✅" if ok else "❌"
            print(f"{status} {name} @ {stock}")
            if not ok and err:
                print(f"   {err[:200].replace(chr(10), ' ')}")

    print("-" * 60)
    ok_count = sum(1 for r in results if r[2])
    print(f"通过: {ok_count}/{len(results)}")
    if ok_count < len(results):
        print("失败明细:")
        for name, stock, ok, err in results:
            if not ok:
                print(f"  {name} @ {stock}")
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
