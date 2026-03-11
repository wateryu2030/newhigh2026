"""交易时间实时调度：每 30 秒更新行情与涨停池。"""
from __future__ import annotations

import time

def run_realtime_loop(interval_seconds: int = 30) -> None:
    from ..collectors.realtime_quotes import update_realtime_quotes
    from ..collectors.limit_up import update_limitup

    while True:
        try:
            n1 = update_realtime_quotes()
            n2 = update_limitup()
            print(f"实时更新: 行情 {n1} 条, 涨停 {n2} 条")
        except Exception as e:
            print("realtime_scheduler error:", e)
        time.sleep(interval_seconds)
