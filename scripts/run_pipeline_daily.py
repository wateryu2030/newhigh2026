#!/usr/bin/env python3
"""每日数据管道：股票池、资金流、龙虎榜。建议 18:00 定时执行。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data-pipeline", "src"))
sys.path.insert(0, os.path.join(ROOT, "data-engine", "src"))
sys.path.insert(0, os.path.join(ROOT, "core", "src"))

if __name__ == "__main__":
    from data_pipeline.scheduler.daily_scheduler import run_daily
    run_daily(update_all_kline=False, kline_codes_limit=0)
