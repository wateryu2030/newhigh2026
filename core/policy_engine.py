# -*- coding: utf-8 -*-
"""
政策引擎：政策/新闻对板块与市场的影响，用于仓位与龙头池权重微调。
当前为轻量实现，可后续接入新闻爬虫或 LLM 解读。
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_policy_signal() -> Dict[str, Any]:
    """
    当前政策/新闻面综合信号。
    :return: {"bias": "neutral"|"bullish"|"bearish", "score": 0~100, "highlights": []}
    """
    try:
        from news.collectors import fetch_all_news
        raw = fetch_all_news()
        highlights = [r.get("title") or str(r) for r in (raw or [])[:20] if r]
    except Exception:
        highlights = []
    # 简单规则：无数据则中性
    if not highlights:
        return {"bias": "neutral", "score": 50, "highlights": []}
    # 可扩展：根据关键词或 LLM 判断 bias
    return {"bias": "neutral", "score": 50, "highlights": highlights[:10]}


def get_sector_policy_impact(sector_names: List[str]) -> Dict[str, float]:
    """
    各板块政策影响系数 0~1，用于龙头池内板块加权。
    当前返回中性，后续可对接主题/政策标签。
    """
    return {s: 0.5 for s in sector_names}
