#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
机构级闭环每周调度：情绪回测验证 → 龙虎榜胜率统计 → 融合策略权重/报告 → 输出 weekly_strategy_report.json
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)


def main():
    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    report = {
        "generated_at": datetime.now().isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "emotion_backtest": None,
        "lhb_statistics": None,
        "fusion_note": "run backtest with fusion_strategy for full report",
    }

    # 1. 情绪回测验证
    try:
        from backtest.emotion_labeler import generate_emotion_history
        from backtest.emotion_backtest import run_emotion_backtest_from_bars, DEFAULT_EMOTION_CACHE, DEFAULT_REPORT_PATH
        from database.duckdb_backend import DuckDBBackend
        import pandas as pd

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

    # 2. 龙虎榜胜率统计
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
    print("weekly_strategy_report.json written to", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
