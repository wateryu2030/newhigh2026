"""
统一系统运行入口：数据更新 → 市场扫描 → AI 分析 → 策略生成 → 系统监控，循环执行。
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from system_core.repo_paths import prepend_repo_sources

_ROOT = prepend_repo_sources()
try:
    from core.logging_config import configure_logging

    configure_logging()
except (ImportError, RuntimeError, OSError):
    pass


def run_once(
    run_data: bool = True,
    run_scan: bool = True,
    run_ai: bool = True,
    run_strategy: bool = True,
    data_include_daily_kline: bool = False,
    data_daily_kline_limit: int = 0,
) -> dict:
    """
    执行一轮：数据 → 扫描 → AI → 策略 → 监控。
    返回各阶段结果与监控状态。
    """
    from system_core.data_orchestrator import update as data_update
    from system_core.scan_orchestrator import run as scan_run
    from system_core.ai_orchestrator import run as ai_run
    from system_core.strategy_orchestrator import run as strategy_run
    from system_core.system_monitor import record as monitor_record

    data_result = None
    if run_data:
        data_result = data_update(
            run_stock_list=True,
            run_daily_kline=data_include_daily_kline,
            run_realtime=True,
            run_fundflow=True,
            run_limitup=True,
            run_longhubang=True,
            daily_kline_codes_limit=data_daily_kline_limit,
        )

    scan_result = None
    if run_scan:
        scan_result = scan_run()

    ai_result = None
    if run_ai:
        ai_result = ai_run()

    strategy_result = None
    if run_strategy:
        strategy_result = strategy_run()

    status = monitor_record(
        data_result=data_result,
        scan_result=scan_result,
        ai_result=ai_result,
        strategy_result=strategy_result,
    )
    return {
        "data": data_result,
        "scan": scan_result,
        "ai": ai_result,
        "strategy": strategy_result,
        "status": status,
    }


def run_loop(
    interval_seconds: int = 60,
    run_data: bool = True,
    run_scan: bool = True,
    run_ai: bool = True,
    run_strategy: bool = True,
    data_include_daily_kline: bool = False,
    data_daily_kline_limit: int = 0,
) -> None:
    """
    主循环：每 interval_seconds 秒执行一轮 data → scan → ai → strategy → monitor。
    """
    while True:
        try:
            run_once(
                run_data=run_data,
                run_scan=run_scan,
                run_ai=run_ai,
                run_strategy=run_strategy,
                data_include_daily_kline=data_include_daily_kline,
                data_daily_kline_limit=data_daily_kline_limit,
            )
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            print(f"Loop error: {e}", flush=True)
        time.sleep(interval_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description="统一系统运行核心：数据 → 扫描 → AI → 策略 → 监控")
    parser.add_argument("--once", action="store_true", help="只跑一轮后退出")
    parser.add_argument("--interval", type=int, default=60, help="循环间隔秒数（默认 60）")
    parser.add_argument("--no-data", action="store_true", help="跳过数据更新")
    parser.add_argument("--no-scan", action="store_true", help="跳过扫描")
    parser.add_argument("--no-ai", action="store_true", help="跳过 AI 分析")
    parser.add_argument("--no-strategy", action="store_true", help="跳过策略生成")
    parser.add_argument(
        "--daily-kline", action="store_true", help="本轮包含日 K 批量更新（仅 once 或首轮有效）"
    )
    parser.add_argument(
        "--daily-kline-limit", type=int, default=0, help="日 K 更新标的数上限（默认 0 不更新）"
    )
    args = parser.parse_args()

    os.chdir(_ROOT)

    if args.once:
        result = run_once(
            run_data=not args.no_data,
            run_scan=not args.no_scan,
            run_ai=not args.no_ai,
            run_strategy=not args.no_strategy,
            data_include_daily_kline=args.daily_kline,
            data_daily_kline_limit=args.daily_kline_limit or (100 if args.daily_kline else 0),
        )
        print("Status:", result.get("status"))
        return 0

    run_loop(
        interval_seconds=args.interval,
        run_data=not args.no_data,
        run_scan=not args.no_scan,
        run_ai=not args.no_ai,
        run_strategy=not args.no_strategy,
        data_include_daily_kline=args.daily_kline,
        data_daily_kline_limit=args.daily_kline_limit or 0,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
