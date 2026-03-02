#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机构闭环定时任务：交易日晚上 22:00 自动执行情绪回测 + 龙虎榜胜率 + 每周报告，避免白天手动触发卡顿。
用法：
  --once    执行一次后退出（供 crontab 调用）
  无参数    常驻进程，每天 22:00（仅交易日）执行一次
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)


def is_trading_day(dt: datetime) -> bool:
    """A 股交易日：周一至周五（暂不考虑节假日）。"""
    return dt.weekday() < 5  # 0=Mon .. 4=Fri


def run_pipeline() -> int:
    """执行完整闭环：情绪回测 → 龙虎榜统计 → 每周报告。"""
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    report = {
        "generated_at": datetime.now().isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "emotion_backtest": None,
        "lhb_statistics": None,
    }

    # 1. 情绪回测
    try:
        from backtest.emotion_labeler import generate_emotion_history
        from backtest.emotion_backtest import run_emotion_backtest_from_bars, DEFAULT_EMOTION_CACHE
        from database.duckdb_backend import DuckDBBackend

        generate_emotion_history(start_date=start_date, end_date=end_date)
        backend = DuckDBBackend()
        stocks = backend.get_stocks_from_daily_bars()
        order_book_id = stocks[0][0] if stocks else "000001.XSHE"
        bars = backend.get_daily_bars(order_book_id, start_date=start_date, end_date=end_date)
        if bars is not None and len(bars) > 0:
            emotion_result = run_emotion_backtest_from_bars(bars, start_date, end_date, DEFAULT_EMOTION_CACHE)
            report["emotion_backtest"] = emotion_result
            os.makedirs(os.path.join(_root, "output"), exist_ok=True)
            with open(os.path.join(_root, "output", "emotion_performance_report.json"), "w", encoding="utf-8") as f:
                json.dump({"start_date": start_date, "end_date": end_date, **emotion_result}, f, ensure_ascii=False, indent=2)
        report["emotion_report_path"] = "output/emotion_performance_report.json"
    except Exception as e:
        report["emotion_backtest_error"] = str(e)

    # 2. 龙虎榜胜率
    try:
        from analysis.lhb_statistics import run_lhb_statistics

        lhb_report = run_lhb_statistics(start_date=start_date, end_date=end_date, years=2)
        report["lhb_statistics"] = {
            "by_seat_count": len(lhb_report.get("by_seat", {})),
            "ranking_sample": lhb_report.get("ranking", [])[:5],
        }
        report["lhb_report_path"] = "output/lhb_statistics_report.json"
    except Exception as e:
        report["lhb_statistics_error"] = str(e)

    out_path = os.path.join(_root, "output", "weekly_strategy_report.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[{datetime.now().isoformat()}] weekly_strategy_report.json written")
    return 0


def next_22_trading_day() -> datetime:
    """下一个交易日 22:00 的 datetime（本地时间）。"""
    now = datetime.now()
    target = now.replace(hour=22, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    while not is_trading_day(target):
        target += timedelta(days=1)
    return target


def main():
    parser = argparse.ArgumentParser(description="机构闭环定时：交易日 22:00 执行")
    parser.add_argument("--once", action="store_true", help="执行一次后退出（供 crontab 使用）")
    args = parser.parse_args()

    if args.once:
        return run_pipeline()

    # 常驻：等到下一个交易日 22:00 再执行
    while True:
        next_run = next_22_trading_day()
        print(f"[{datetime.now().isoformat()}] 下次执行: {next_run.isoformat()} (交易日 22:00)")
        while datetime.now() < next_run:
            time.sleep(60)
        run_pipeline()


if __name__ == "__main__":
    sys.exit(main())
