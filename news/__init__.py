# -*- coding: utf-8 -*-
"""
新闻媒体采集与舆情分析。
支持：东方财富、财新、抖音（占位）、简单舆情分析。
"""
from .collectors import (
    fetch_eastmoney_news,
    fetch_caixin_news,
    fetch_douyin_news_placeholder,
    fetch_all_news,
)
from .sentiment import (
    SentimentAnalyzer,
    analyze_sentiment,
    aggregate_sentiment,
)

__all__ = [
    "fetch_eastmoney_news",
    "fetch_caixin_news",
    "fetch_douyin_news_placeholder",
    "fetch_all_news",
    "SentimentAnalyzer",
    "analyze_sentiment",
    "aggregate_sentiment",
]
