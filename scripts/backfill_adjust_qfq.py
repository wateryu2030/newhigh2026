#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复权补全：对全市场（或指定标的）在给定日期区间内用 前复权(qfq)+后复权(hfq) 拉取并写入库，
覆盖已有日线，在数据更新时补齐双轨。可与全量同步配合使用。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)


def main():
    import argparse
    from datetime import datetime, timedelta
    from database.data_fetcher import DataFetcher, get_all_a_share_code_name

    parser = argparse.ArgumentParser(description="全量复权补全：前复权(qfq)+后复权(hfq)覆盖指定区间日线")
    parser.add_argument("--start", default=None, help="开始日期 YYYYMMDD，默认三年前")
    parser.add_argument("--end", default=None, help="结束日期 YYYYMMDD，默认今天")
    parser.add_argument("--delay", type=float, default=0.12, help="每只股票请求间隔(秒)")
    parser.add_argument("--limit", type=int, default=None, help="仅处理前 N 只（用于测试）")
    args = parser.parse_args()

    start = args.start or (datetime.now() - timedelta(days=365 * 3)).strftime("%Y%m%d")
    end = args.end or datetime.now().strftime("%Y%m%d")

    code_name = get_all_a_share_code_name()
    symbols = [c for c, _ in code_name]
    code_name_map = {c: n for c, n in code_name}
    if not symbols:
        print("未获取到股票列表")
        return 1
    if args.limit:
        symbols = symbols[: args.limit]
        code_name_map = {c: code_name_map.get(c, "") for c in symbols}
        print(f"（仅处理前 {len(symbols)} 只）")

    fetcher = DataFetcher()
    n = fetcher.backfill_adjust(
        symbols=symbols,
        start_date=start,
        end_date=end,
        delay=args.delay,
        code_name_map=code_name_map,
    )
    print(f"复权补全完成: {n}/{len(symbols)} 只（qfq+hfq）")
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
