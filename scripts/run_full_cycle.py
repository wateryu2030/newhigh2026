#!/usr/bin/env python3
"""
一键执行：先填充 quant_system.duckdb 保证数据量，再跑 AI 终端单轮（扫描 → 情绪/游资/主线 → 融合信号）。
适合每日定时或手动跑一次，支撑前端 AI 交易页与策略分析。
"""

from __future__ import annotations

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
for d in [
    "data-pipeline/src",
    "market-scanner/src",
    "ai-models/src",
    "strategy-engine/src",
    "core/src",
]:
    p = os.path.join(ROOT, d)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
_opt = os.path.join(ROOT, "ai-optimizer/src")
if os.path.isdir(_opt) and _opt not in sys.path:
    sys.path.insert(0, _opt)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Full cycle: ensure market data + run terminal loop (scanner → AI → signals)."
    )
    parser.add_argument(
        "--skip-data", action="store_true", help="Skip data fill; only run scanner + AI + signals"
    )
    parser.add_argument(
        "--quick-data", action="store_true", help="Quick data: 60 days, 300 symbols, no realtime"
    )
    parser.add_argument(
        "--days", type=int, default=250, help="Days of history when not --quick-data (default 250)"
    )
    parser.add_argument(
        "--max-symbols",
        type=int,
        default=800,
        help="Max symbols for klines when not --quick-data (default 800)",
    )
    args = parser.parse_args()

    if not args.skip_data:
        from ensure_market_data import run as ensure_run

        if args.quick_data:
            ensure_run(
                days_back=60,
                max_symbols=300,
                delay_seconds=0.1,
                skip_kline=False,
                skip_realtime=True,
            )
        else:
            ensure_run(
                days_back=args.days,
                max_symbols=args.max_symbols,
                delay_seconds=0.15,
                skip_kline=False,
                skip_realtime=True,
            )

    # Terminal loop: scanner → AI → fusion signals
    from run_terminal_loop import main as terminal_main

    return terminal_main()


if __name__ == "__main__":
    sys.exit(main())
