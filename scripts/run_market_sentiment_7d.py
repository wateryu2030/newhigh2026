#!/usr/bin/env python3
"""输出全市场 7 维情绪 JSON；可先跑实时采集再计算。"""
import json
import os
import sys

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

if __name__ == "__main__":
    if os.environ.get("UPDATE_REALTIME_FIRST"):
        try:
            from data_pipeline.collectors.realtime_quotes import update_realtime_quotes

            n = update_realtime_quotes()
            print(f"realtime rows inserted: {n}", file=sys.stderr)
        except Exception as ex:
            print(f"realtime update skip: {ex}", file=sys.stderr)
    from data_pipeline.sentiment_7d import get_market_sentiment_7d

    print(json.dumps(get_market_sentiment_7d(), ensure_ascii=False, indent=2))
