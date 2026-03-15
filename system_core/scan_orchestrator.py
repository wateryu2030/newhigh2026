"""
市场扫描调度：执行 limit_up、fund_flow、volume_spike、trend 扫描与 hotmoney_sniper。
"""

from __future__ import annotations

from typing import Dict, Any


def run() -> Dict[str, Any]:
    """执行全部扫描器 + 游资狙击，返回各步骤产出条数。"""
    result = {
        "limit_up": 0,
        "fund_flow": 0,
        "volume_spike": 0,
        "trend": 0,
        "sniper": 0,
        "errors": [],
    }
    try:
        from market_scanner import (
            run_limit_up_scanner,
            run_fund_flow_scanner,
            run_volume_spike_scanner,
            run_trend_scanner,
            run_sniper,
        )
    except ImportError as e:
        result["errors"].append(str(e))
        return result

    try:
        result["limit_up"] = run_limit_up_scanner()
    except Exception as e:
        result["errors"].append(f"limit_up: {e}")
    try:
        result["fund_flow"] = run_fund_flow_scanner()
    except Exception as e:
        result["errors"].append(f"fund_flow: {e}")
    try:
        result["volume_spike"] = run_volume_spike_scanner()
    except Exception as e:
        result["errors"].append(f"volume_spike: {e}")
    try:
        result["trend"] = run_trend_scanner()
    except Exception as e:
        result["errors"].append(f"trend: {e}")
    try:
        result["sniper"] = run_sniper(min_score=0.7, top_n=50)
    except Exception as e:
        result["errors"].append(f"sniper: {e}")

    return result
