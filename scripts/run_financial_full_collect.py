#!/usr/bin/env python3
"""
全量财报+十大股东采集，写入 DuckDB

用法:
  python3 scripts/run_financial_full_collect.py           # 全量
  python3 scripts/run_financial_full_collect.py --limit 50  # 测试 50 只
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data" / "src"))
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "core" / "src"))

from data.collectors.financial_report import FinancialReportCollector


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="限制采集数量")
    p.add_argument("--delay", type=float, default=0.3, help="每只间隔秒数")
    args = p.parse_args()

    collector = FinancialReportCollector()
    stocks = collector.get_company_list()
    if stocks.empty:
        print("❌ 获取股票列表失败")
        return 1

    codes = stocks["code"].tolist()
    if args.limit:
        codes = codes[: args.limit]
        print(f"限制采集 {args.limit} 只")

    print(f"开始全量采集 {len(codes)} 只股票（财报+十大股东）...")
    stats = collector.collect_all_stocks(
        stock_codes=codes,
        delay_seconds=args.delay,
    )
    print(f"\n完成: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
