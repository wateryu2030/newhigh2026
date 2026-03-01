# -*- coding: utf-8 -*-
"""
Skill 2: Theme Heat
利用 LLM 从新闻中提取热门概念和行业主题，并评估其热度
"""
from __future__ import annotations
import os
import sys
from typing import Any, List, Dict
from collections import Counter

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def _extract_themes_fallback(news_list: List[Dict]) -> List[str]:
    """备用：基于关键词提取主题（当LLM不可用时）"""
    # 预定义的热门主题关键词
    theme_keywords = {
        "低空经济": ["低空", "飞行汽车", "eVTOL", "通用航空"],
        "人工智能": ["AI", "人工智能", "大模型", "算力", "ChatGPT"],
        "机器人": ["机器人", "人形机器人", "具身智能"],
        "新能源": ["新能源", "光伏", "风电", "储能", "锂电池"],
        "半导体": ["半导体", "芯片", "集成电路", "光刻胶"],
        "华为概念": ["华为", "鸿蒙", "欧拉", "昇腾"],
        "数字经济": ["数字经济", "数据要素", "数据确权"],
        "元宇宙": ["元宇宙", "VR", "AR", "虚拟现实"],
        "生物医药": ["医药", "创新药", "CXO", "疫苗"],
        "自动驾驶": ["自动驾驶", "无人驾驶", "智能网联"],
    }
    
    # 统计每个主题在新闻中的出现频次
    theme_scores = {}
    for news in news_list:
        text = f"{news.get('title', '')} {news.get('content', '')}"
        for theme, keywords in theme_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                theme_scores[theme] = theme_scores.get(theme, 0) + score
    
    # 返回按频次排序的主题
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_themes[:15]]  # 返回前15个


def execute(ctx, llm_client=None) -> Any:
    """
    提取热门主题
    
    :param ctx: SkillContext
    :param llm_client: LLM客户端（可选）
    :return: 更新后的ctx
    """
    news_texts = [
        f"{n.get('title', '')} {n.get('content', '')}"
        for n in ctx.news_raw
    ]
    
    if not news_texts:
        ctx.themes_raw = []
        return ctx
    
    themes = []
    
    # 尝试使用LLM提取
    if llm_client:
        try:
            llm_themes = llm_client.extract_themes(news_texts)
            themes = [t.get("name", "") for t in llm_themes if t.get("name")]
        except Exception as e:
            print(f"[ThemeHeat] LLM提取失败，使用备用方案: {e}")
            themes = _extract_themes_fallback(ctx.news_raw)
    else:
        # 使用备用方案
        themes = _extract_themes_fallback(ctx.news_raw)
    
    ctx.themes_raw = themes
    
    return ctx
