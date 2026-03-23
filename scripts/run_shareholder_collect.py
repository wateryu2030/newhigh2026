#!/usr/bin/env python3
"""
十大股东多期历史采集 - 自动化入口

akshare.stock_main_stock_holder 单次调用即返回该股全部历史期（约 100+ 期），
采集器已改为按 截至日期 分组逐期写入。每只股票一次请求即补齐 5 年数据。

用法:
  # 全量采集（5000+ 股，约 40 分钟）
  python scripts/run_shareholder_collect.py

  # 测试 10 只
  python scripts/run_shareholder_collect.py --limit 10

  # 只采集股东（跳过财报）
  python scripts/run_shareholder_collect.py --shareholders-only

  # 按文件 / 代码列表补采
  python scripts/run_shareholder_collect.py --shareholders-only --stocks-file reports/missing_stocks.txt
  python scripts/run_shareholder_collect.py --shareholders-only --codes 000001,600519

  # 快速模式（0.2 秒间隔）
  python scripts/run_shareholder_collect.py --delay 0.2

配合 LaunchAgent 每日自动执行:
  launchctl load ~/Library/LaunchAgents/com.newhigh.shareholder-collect.plist
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "data" / "src"))
sys.path.insert(0, str(ROOT / "lib"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="十大股东多期历史采集",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制采集股票数量（测试用）",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.6,
        help="每只股票间隔秒数（默认 0.6，降低 No tables found 失败率）",
    )
    parser.add_argument(
        "--shareholders-only",
        action="store_true",
        help="仅采集股东，不采集财报",
    )
    parser.add_argument(
        "--skip-have-periods",
        type=int,
        default=0,
        help="跳过已有报告期数≥N 的股票（补采失败项时用，如 --skip-have-periods 10）",
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="full=全量，incremental=只补缺",
    )
    parser.add_argument(
        "--codes",
        type=str,
        default="",
        help="仅采集逗号分隔的股票代码（与全市场列表互斥）",
    )
    parser.add_argument(
        "--stocks-file",
        type=str,
        default="",
        help="从文件读取代码，一行一个（可与 --codes 二选一或合并，文件优先于 codes）",
    )
    args = parser.parse_args()

    from data.collectors.financial_report import FinancialReportCollector

    collector = FinancialReportCollector()

    explicit: list[str] = []
    if args.stocks_file.strip():
        fp = Path(args.stocks_file)
        if not fp.is_file():
            print(f"股票列表文件不存在: {fp}")
            return 1
        for line in fp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            explicit.append(line.split(",")[0].strip())
    if args.codes.strip():
        explicit.extend([c.strip() for c in args.codes.split(",") if c.strip()])

    if explicit:
        # 去重保持顺序
        seen: set[str] = set()
        codes = []
        for c in explicit:
            if c not in seen:
                seen.add(c)
                codes.append(c)
        print(f"指定股票 {len(codes)} 只（来自 --stocks-file / --codes）")
    else:
        stocks = collector.get_company_list()
        if stocks.empty:
            print("获取股票列表失败")
            return 1

        codes = stocks["code"].tolist()
        if args.limit:
            codes = codes[: args.limit]
            print(f"限制采集 {args.limit} 只")

    if args.shareholders_only:
        skip_threshold = args.skip_have_periods
        if skip_threshold > 0:
            from lib.database import get_connection
            conn = get_connection(read_only=False)
            if conn:
                have = conn.execute("""
                    SELECT stock_code FROM (
                        SELECT stock_code, COUNT(DISTINCT report_date) as cnt
                        FROM top_10_shareholders GROUP BY stock_code
                    ) WHERE cnt >= ?
                """, [skip_threshold]).fetchdf()
                conn.close()
                skip_set = set(have["stock_code"].astype(str)) if not have.empty else set()
                codes = [c for c in codes if str(c) not in skip_set]
                print(f"跳过已有≥{skip_threshold}期的股票，剩余 {len(codes)} 只")
        print(f"仅采集股东，共 {len(codes)} 只...")
        success = 0
        total_periods = 0
        for i, code in enumerate(codes, 1):
            try:
                holders = collector.get_top_10_shareholders(code)
                if holders is not None and not holders.empty:
                    n = collector.save_top_10_shareholders(code, holders)
                    if n > 0:
                        success += 1
                        total_periods += n
            except Exception as e:
                print(f"  {code}: {e}")
            if i % 100 == 0 or i == len(codes):
                print(f"进度 {i}/{len(codes)}，成功 {success}，累计 {total_periods} 期")
            if i < len(codes):
                import time
                import random
                time.sleep(args.delay + random.uniform(0, 0.3))  # 随机抖动 0~0.3s
        print(f"完成: 成功 {success} 只，共写入 {total_periods} 个报告期")
        return 0

    stats = collector.collect_all_stocks(
        stock_codes=codes,
        delay_seconds=args.delay,
    )
    print(f"\n完成: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
