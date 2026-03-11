#!/usr/bin/env python3
"""
拉取 Tushare 日 K：加载 .env 后执行 data_pipeline.run_incremental("tushare_daily")。
用法（在仓库根目录）：
  python scripts/run_tushare_incremental.py
  python scripts/run_tushare_incremental.py --full   # 全量
"""
from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# 先加载 .env（TUSHARE_TOKEN）
_env = os.path.join(ROOT, ".env")
if os.path.isfile(_env):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass

for _d in ["data-pipeline/src", "core/src"]:
    _p = os.path.join(ROOT, _d)
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tushare 日 K 增量/全量拉取")
    parser.add_argument("--full", action="store_true", help="全量拉取（忽略已有最新日期）")
    args = parser.parse_args()

    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        print("未设置 TUSHARE_TOKEN，请在 .env 或环境变量中配置")
        return 1

    from data_pipeline import run_incremental

    try:
        n = run_incremental("tushare_daily", force_full=args.full)
        print(f"tushare_daily 写入行数: {n}")
        return 0
    except Exception as e:
        print(f"拉取失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
