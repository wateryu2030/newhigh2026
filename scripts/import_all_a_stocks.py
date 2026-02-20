#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全量导入 A 股：获取沪深京全部股票列表，从 AKShare 拉取日线并写入本地数据库。
数据量约几千只 × 约 500 交易日，首次运行需较长时间（约 1～3 小时，视网络与 delay 而定）。
支持断点续传：默认跳过已有数据的股票，可多次执行直至全部完成。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def main():
    import argparse
    from datetime import datetime, timedelta
    from database.data_fetcher import DataFetcher, get_all_a_share_symbols

    parser = argparse.ArgumentParser(description="全量导入 A 股日线到本地数据库")
    parser.add_argument("--start", default=None, help="开始日期 YYYYMMDD，默认两年前")
    parser.add_argument("--end", default=None, help="结束日期 YYYYMMDD，默认今天")
    parser.add_argument("--delay", type=float, default=0.12, help="每只股票请求间隔(秒)，避免限流")
    parser.add_argument("--no-skip", action="store_true", help="不跳过已有数据，全部重新拉取")
    parser.add_argument("--limit", type=int, default=None, help="仅拉取前 N 只（用于测试）")
    args = parser.parse_args()

    start = args.start or (datetime.now() - timedelta(days=365 * 2)).strftime("%Y%m%d")
    end = args.end or datetime.now().strftime("%Y%m%d")

    symbols = get_all_a_share_symbols()
    print(f"A 股列表: 共 {len(symbols)} 只")
    if not symbols:
        print("未获取到股票列表，请检查网络与 akshare 版本")
        return 1
    if args.limit:
        symbols = symbols[: args.limit]
        print(f"（仅处理前 {len(symbols)} 只）")

    fetcher = DataFetcher()
    if args.limit:
        n = fetcher.fetch_multiple_stocks(symbols, start, end, delay=args.delay)
    else:
        n = fetcher.fetch_all_a_stocks(
            start_date=start,
            end_date=end,
            delay=args.delay,
            skip_existing=not args.no_skip,
        )
    print(f"\n全量导入完成: 成功 {n} 只")
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
