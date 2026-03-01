# -*- coding: utf-8 -*-
"""
Skill 3: Canonicalize
将提取的主题名称标准化（映射到标准板块名），并进行去重和别名处理
"""
from __future__ import annotations
import os
import sys
from typing import Any, List, Dict

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


# 主题别名映射表
THEME_ALIASES = {
    # AI相关
    "人工智能": ["AI", "大模型", "GPT", "ChatGPT", "AIGC", "生成式AI"],
    "算力": ["AI算力", "智算中心", "算力租赁", "算力基础设施"],
    "人形机器人": ["具身智能", "仿生机器人", "仿人机器人"],
    
    # 新能源
    "新能源": ["清洁能源", "可再生能源", "绿色能源"],
    "光伏": ["太阳能", "光伏发电"],
    "储能": ["储能电池", "电化学储能", "新型储能"],
    "锂电池": ["动力电池", "锂离子电池", "固态电池"],
    
    # 科技
    "半导体": ["芯片", "集成电路", "IC"],
    "光刻胶": ["光刻机材料", "半导体材料"],
    "华为概念": ["华为产业链", "华为链"],
    "鸿蒙": ["HarmonyOS", "鸿蒙系统"],
    
    # 其他
    "低空经济": ["低空飞行", "通用航空", "飞行汽车"],
    "自动驾驶": ["无人驾驶", "智能驾驶", "智能网联汽车"],
    "元宇宙": ["Metaverse", "虚拟世界"],
    "数字经济": ["数字化", "产业数字化"],
}


def _canonicalize_theme(theme: str) -> str:
    """标准化单个主题名称"""
    theme = theme.strip()
    
    # 检查是否是某个标准主题的别名
    for canonical, aliases in THEME_ALIASES.items():
        if theme == canonical or theme in aliases:
            return canonical
    
    return theme


def _merge_similar_themes(themes: List[str]) -> List[str]:
    """合并相似主题"""
    canonical_map = {}
    
    for theme in themes:
        canonical = _canonicalize_theme(theme)
        canonical_map[canonical] = canonical_map.get(canonical, 0) + 1
    
    # 返回按频次排序的唯一主题
    sorted_themes = sorted(canonical_map.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_themes]


def execute(ctx, llm_client=None) -> Any:
    """
    标准化主题名称
    
    :param ctx: SkillContext
    :param llm_client: LLM客户端（可选）
    :return: 更新后的ctx
    """
    raw_themes = ctx.themes_raw
    
    if not raw_themes:
        ctx.themes_canonical = []
        return ctx
    
    # 标准化和去重
    canonical_themes = _merge_similar_themes(raw_themes)
    
    ctx.themes_canonical = canonical_themes
    
    return ctx
