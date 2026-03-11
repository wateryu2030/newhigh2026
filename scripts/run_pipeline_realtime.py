#!/usr/bin/env python3
"""实时数据管道：每 30 秒更新行情与涨停池。交易时间运行。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "data-pipeline", "src"))
sys.path.insert(0, os.path.join(ROOT, "core", "src"))

if __name__ == "__main__":
    from data_pipeline.scheduler.realtime_scheduler import run_realtime_loop
    run_realtime_loop(interval_seconds=30)
