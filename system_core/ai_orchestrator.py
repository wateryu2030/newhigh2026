"""
AI 分析调度：执行情绪周期、游资席位、主线题材。
"""

from __future__ import annotations

from typing import Dict, Any


def run() -> Dict[str, Any]:
    """执行 emotion_cycle、hotmoney_detector、sector_rotation_ai，返回状态与条数。"""
    result = {
        "emotion": None,
        "hotmoney": 0,
        "sector": 0,
        "errors": [],
    }
    try:
        from ai_models import run_emotion_cycle, run_hotmoney_detector, run_sector_rotation_ai
    except ImportError as e:
        result["errors"].append(str(e))
        return result

    try:
        stage = run_emotion_cycle()
        result["emotion"] = stage
    except Exception as e:
        result["errors"].append(f"emotion: {e}")
    try:
        result["hotmoney"] = run_hotmoney_detector()
    except Exception as e:
        result["errors"].append(f"hotmoney: {e}")
    try:
        result["sector"] = run_sector_rotation_ai()
    except Exception as e:
        result["errors"].append(f"sector: {e}")

    return result
