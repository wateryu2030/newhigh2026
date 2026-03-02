# -*- coding: utf-8 -*-
"""
龙虎榜回测：调用 lhb_statistics 跑胜率统计，输出报告与排行榜。
"""
from __future__ import annotations
from typing import Any, Dict, Optional

from analysis.lhb_statistics import run_lhb_statistics, DEFAULT_REPORT_PATH


def run_lhb_backtest(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    years: int = 2,
    report_path: Optional[str] = None,
) -> Dict[str, Any]:
    """运行龙虎榜胜率统计并返回报告。"""
    return run_lhb_statistics(
        start_date=start_date,
        end_date=end_date,
        years=years,
        report_path=report_path or DEFAULT_REPORT_PATH,
    )
