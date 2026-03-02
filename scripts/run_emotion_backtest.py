#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪周期回测验证：生成历史情绪标签 + 按情绪分组统计收益，输出 emotion_performance_report.json。
运行时间目标 < 5 分钟。
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

    from backtest.emotion_labeler import generate_emotion_history
    from backtest.emotion_backtest import run_emotion_backtest_from_bars
    from database.duckdb_backend import DuckDBBackend

    generate_emotion_history(start_date=start_date, end_date=end_date)
    backend = DuckDBBackend()
    stocks = backend.get_stocks_from_daily_bars()
    order_book_id = stocks[0][0] if stocks else "000001.XSHE"
    bars = backend.get_daily_bars(order_book_id, start_date=start_date, end_date=end_date)
    if bars is None or len(bars) == 0:
        print("No bars for", order_book_id, "- ensure DB has daily_bars")
        sys.exit(1)
    result = run_emotion_backtest_from_bars(bars, start_date, end_date)
    os.makedirs(os.path.join(_root, "output"), exist_ok=True)
    out_path = os.path.join(_root, "output", "emotion_performance_report.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"start_date": start_date, "end_date": end_date, **result}, f, ensure_ascii=False, indent=2)
    print("Written:", out_path)
    print("Summary:", result.get("summary", {}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
