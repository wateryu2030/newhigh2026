#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量同步股票池：根据 data/ 下策略用到的 CSV 收集所有股票代码，从 AKShare 拉取日线并写入数据库。
运行后多标的策略（如策略2、策略1）回测时「No market data」会明显减少。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def main():
    import argparse
    from datetime import datetime, timedelta
    from database.data_fetcher import DataFetcher, get_pool_symbols

    parser = argparse.ArgumentParser(description="全量同步策略股票池数据到数据库")
    parser.add_argument("--start", default=None, help="开始日期 YYYYMMDD，默认两年前")
    parser.add_argument("--end", default=None, help="结束日期 YYYYMMDD，默认今天")
    parser.add_argument("--delay", type=float, default=0.15, help="每只股票请求间隔(秒)")
    args = parser.parse_args()

    start = args.start or (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
    end = args.end or datetime.now().strftime("%Y%m%d")

    symbols = get_pool_symbols()
    print(f"当前股票池: {len(symbols)} 只")
    if not symbols:
        print("请确保 data/ 下存在 industry_stock_map.csv、tech_leader_stocks.csv、consume_leader_stocks.csv 等")
        return 1

    fetcher = DataFetcher()
    n = fetcher.fetch_pool_stocks(start_date=start, end_date=end, delay=args.delay)
    print(f"\n全量同步完成: {n}/{len(symbols)} 只成功")
    return 0 if n > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
