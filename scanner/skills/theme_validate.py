# -*- coding: utf-8 -*-
"""
Skill 4: Theme Validate
对比本地历史数据，验证主题的连续性，过滤掉纯粹的噪音
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def execute(ctx) -> Any:
    """
    验证主题有效性
    
    :param ctx: SkillContext
    :return: 更新后的ctx
    """
    themes = ctx.themes_canonical
    
    if not themes:
        ctx.themes_validated = []
        return ctx
    
    validated_themes = []
    
    for theme in themes:
        # 这里可以添加更多验证逻辑
        # 例如：检查该主题相关的股票近期表现、资金流向等
        
        # 简单验证：主题在新闻中出现的频次
        mention_count = sum(
            1 for news in ctx.news_raw
            if theme in news.get("title", "") or theme in news.get("content", "")
        )
        
        # 至少需要2条新闻提及才算有效主题
        if mention_count >= 2:
            validated_themes.append({
                "name": theme,
                "mention_count": mention_count,
                "is_valid": True,
            })
    
    ctx.themes_validated = validated_themes
    
    return ctx
