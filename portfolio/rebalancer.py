# -*- coding: utf-8 -*-
"""
组合再平衡：按频率（日/周/月）检查并执行再平衡。
"""
from __future__ import annotations
from datetime import datetime
from typing import List, Optional


class PortfolioRebalancer:
    """
    定期再平衡：当距离上次再平衡超过阈值时触发。
    - daily: 每日
    - weekly: 每周一
    - monthly: 每月首日
    """

    def __init__(self, freq: str = "monthly"):
        self.freq = freq.lower()
        self._last_rebalance_date: Optional[str] = None

    def should_rebalance(self, date_str: str) -> bool:
        """
        :param date_str: 当前日期 YYYY-MM-DD
        :return: 是否应执行再平衡
        """
        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            return False

        if self._last_rebalance_date is None:
            self._last_rebalance_date = date_str
            return True

        if self.freq == "daily":
            return True
        if self.freq == "weekly":
            return dt.weekday() == 0
        if self.freq == "monthly":
            return dt.day == 1
        return False

    def mark_rebalanced(self, date_str: str) -> None:
        """标记已再平衡。"""
        self._last_rebalance_date = date_str
