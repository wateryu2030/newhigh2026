"""
Skill 1: News Fetch
从多源抓取财经新闻与热点（东方财富多关键词、财新等），支持更多新闻与自媒体内容，供主题热点自动发现。
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def execute(ctx, days_lookback: int = 3) -> Any:
    """
    抓取财经新闻（多源、多关键词，以获取更多新闻与自媒体内容）。
    :param ctx: SkillContext
    :param days_lookback: 回溯天数（当前由 limit 控制条数）
    :return: 更新后的ctx
    """
    try:
        from news import fetch_all_news

        # 全市场热点：不指定个股，拉取多关键词/指数新闻，得到更多内容
        raw_news = fetch_all_news(
            symbol="",  # 空表示全市场，内部用多关键词拉取
            sources=["eastmoney", "caixin"],
            limit_per_source=80,
        )

        news_list = []
        for source, items in raw_news.items():
            for item in items:
                if item and not item.get("error"):
                    news_list.append({
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "source": item.get("source", source),
                        "source_site": item.get("source_site", source),
                        "publish_time": item.get("publish_time", ""),
                        "url": item.get("url", ""),
                        "sentiment_label": item.get("sentiment_label", "neutral"),
                    })

        news_list.sort(
            key=lambda x: x.get("publish_time", ""),
            reverse=True
        )
        # 保留更多条以支撑主题热点来自更多新闻
        ctx.news_raw = news_list[:250]

    except Exception as e:
        print(f"[NewsFetch] 获取新闻失败: {e}")
        ctx.news_raw = []

    return ctx
