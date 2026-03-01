# -*- coding: utf-8 -*-
"""
Skill 1: News Fetch
从 ReadHub、早报等源抓取最近 24-72 小时的财经新闻
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
    抓取财经新闻
    
    :param ctx: SkillContext
    :param days_lookback: 回溯天数
    :return: 更新后的ctx
    """
    # 优先从已有的news模块获取新闻
    try:
        from news import fetch_all_news
        
        # 获取全市场热点新闻（不指定个股）
        # 获取财新网热点新闻
        raw_news = fetch_all_news(
            symbol="",  # 全市场
            sources=["caixin", "eastmoney"],
            limit_per_source=50,
        )
        
        # 整理新闻列表
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
        
        # 按时间排序
        news_list.sort(
            key=lambda x: x.get("publish_time", ""),
            reverse=True
        )
        
        ctx.news_raw = news_list[:100]  # 最多保留100条
        
    except Exception as e:
        print(f"[NewsFetch] 获取新闻失败: {e}")
        ctx.news_raw = []
    
    return ctx
