#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
情绪周期 + 龙虎榜 每日刷新（无需启动 Web）。
供 crontab / Cursor / OpenClaw 自动执行：拉取当日情绪与龙虎榜并写入 data/daily_emotion.json、data/dragon_lhb_pool.json。
用法：在项目根目录执行 python scripts/run_emotion_lhb_daily.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    try:
        from core.sentiment_engine import get_emotion_state, save_daily_emotion_json
        from core.lhb_engine import get_dragon_lhb_pool, save_dragon_lhb_pool_json
    except ImportError as e:
        print("ERROR: 无法导入情绪/龙虎榜模块:", e, file=sys.stderr)
        return 1

    try:
        state = get_emotion_state()
        path1 = save_daily_emotion_json(state=state)
        pool = get_dragon_lhb_pool(emotion_cycle=state.get("emotion_cycle"))
        path2 = save_dragon_lhb_pool_json(pool=pool)
        print("OK emotion:", state.get("emotion_cycle"), "score:", state.get("emotion_score"))
        print("OK daily_emotion:", path1)
        print("OK dragon_lhb_pool:", path2, "resonance_count:", pool.get("resonance_count", 0))
        return 0
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
