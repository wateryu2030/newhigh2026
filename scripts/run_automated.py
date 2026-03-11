#!/usr/bin/env python3
"""
自动化执行：加载 .env 后按顺序执行（可选）Tushare 日 K 拉取 → 全周期（扫描→AI→信号）。
供定时任务或手动一键运行。
用法（在仓库根目录）：
  python scripts/run_automated.py
  python scripts/run_automated.py --no-tushare          # 不拉 Tushare，只跑全周期
  python scripts/run_automated.py --no-full-cycle       # 只拉 Tushare，不跑全周期
  python scripts/run_automated.py --full-cycle-with-data  # 全周期含数据填充（ensure_market_data）
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 先加载 .env
_env = os.path.join(ROOT, ".env")
if os.path.isfile(_env):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass

SCRIPTS = os.path.join(ROOT, "scripts")
for _d in ["data-pipeline/src", "market-scanner/src", "ai-models/src", "strategy-engine/src", "core/src"]:
    _p = os.path.join(ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
_opt = os.path.join(ROOT, "ai-optimizer/src")
if os.path.isdir(_opt) and _opt not in sys.path:
    sys.path.insert(0, _opt)


def run_tushare() -> int:
    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        print("[automated] 未设置 TUSHARE_TOKEN，跳过 Tushare 拉取")
        return 0
    from data_pipeline import run_incremental
    try:
        n = run_incremental("tushare_daily", force_full=False)
        print(f"[automated] tushare_daily 写入行数: {n}")
        return 0
    except Exception as e:
        print(f"[automated] tushare_daily 失败: {e}")
        return 1


def run_full_cycle(skip_data: bool = True) -> int:
    from run_full_cycle import main as full_cycle_main
    # 通过修改 sys.argv 传入 --skip-data
    old_argv = sys.argv
    try:
        sys.argv = [old_argv[0], "--skip-data"] if skip_data else old_argv[:1]
        return full_cycle_main()
    finally:
        sys.argv = old_argv


def main() -> int:
    parser = argparse.ArgumentParser(description="自动化执行：Tushare 拉取 + 全周期（扫描→AI→信号）")
    parser.add_argument("--no-tushare", action="store_true", help="不拉 Tushare，只跑全周期")
    parser.add_argument("--no-full-cycle", action="store_true", help="只拉 Tushare，不跑全周期")
    parser.add_argument("--full-cycle-with-data", action="store_true", help="全周期含数据填充（ensure_market_data，用 akshare）")
    args = parser.parse_args()

    code = 0
    if not args.no_tushare:
        code = run_tushare()
        if code != 0:
            return code
    if not args.no_full_cycle:
        skip_data = not args.full_cycle_with_data
        code = run_full_cycle(skip_data=skip_data)
    print("[automated] 执行完成")
    return code


if __name__ == "__main__":
    sys.exit(main())
