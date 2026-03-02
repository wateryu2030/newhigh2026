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


# 主题别名映射表（扩展：更多概念由新闻检测后归入标准主题）
THEME_ALIASES = {
    # AI 与算力
    "人工智能": ["AI", "大模型", "GPT", "ChatGPT", "AIGC", "生成式AI", "Sora", "Kimi", "Claude", "人工智能概念", "AI概念"],
    "算力": ["AI算力", "智算中心", "算力租赁", "算力基础设施", "CPO", "液冷", "铜缆", "算力概念", "算力板块"],
    "人形机器人": ["具身智能", "仿生机器人", "仿人机器人", "机器人", "人形机器人概念", "机器人概念"],
    # 半导体与科技
    "半导体": ["芯片", "集成电路", "IC", "半导体概念", "芯片概念", "半导体板块"],
    "光刻胶": ["光刻机材料", "半导体材料", "光刻胶概念"],
    "华为概念": ["华为产业链", "华为链", "华为概念", "华为板块"],
    "鸿蒙": ["HarmonyOS", "鸿蒙系统", "鸿蒙概念", "鸿蒙板块"],
    # 新能源与电力
    "新能源": ["清洁能源", "可再生能源", "绿色能源", "新能源概念", "新能源板块"],
    "光伏": ["太阳能", "光伏发电", "光伏概念", "光伏板块"],
    "风电": ["海上风电", "风电概念", "风电板块"],
    "储能": ["储能电池", "电化学储能", "新型储能", "储能概念", "储能板块"],
    "锂电池": ["动力电池", "锂离子电池", "固态电池", "锂电池概念", "锂电板块"],
    "氢能": ["氢燃料电池", "绿氢", "制氢", "氢能概念", "氢能板块"],
    "特高压": ["特高压电网", "电网", "输配电", "特高压概念"],
    "充电桩": ["充电", "换电", "充电网络", "充电桩概念", "充电桩板块"],
    # 数字经济与信创
    "数字经济": ["数字化", "产业数字化", "数据要素", "数据确权", "数字经济概念", "数字经济板块"],
    "信创": ["国产软件", "国产替代", "数据安全", "网络安全", "信创概念", "信创板块"],
    # 消费与制造
    "低空经济": ["低空飞行", "通用航空", "飞行汽车", "eVTOL", "低空经济概念", "低空经济板块"],
    "自动驾驶": ["无人驾驶", "智能驾驶", "智能网联汽车", "车联网", "自动驾驶概念", "自动驾驶板块"],
    "消费电子": ["折叠屏", "MR", "苹果产业链", "手机链", "消费电子概念", "消费电子板块"],
    "元宇宙": ["Metaverse", "虚拟世界", "VR", "AR", "虚拟现实", "MR", "元宇宙概念", "元宇宙板块"],
    # 医药与军工
    "生物医药": ["医药", "创新药", "CXO", "疫苗", "中药", "生物医药概念", "医药板块"],
    "军工": ["航天", "航空", "导弹", "军品", "军工概念", "军工板块"],
    "卫星": ["卫星互联网", "星链", "低轨卫星", "卫星概念", "卫星板块"],
    # 周期与金融
    "消费复苏": ["白酒", "食品饮料", "家电", "零售", "餐饮", "消费复苏概念", "消费板块"],
    "高股息": ["分红", "红利", "股息率", "高股息概念", "红利板块"],
    "出口链": ["出口", "出海", "外销", "出口链概念", "出口板块"],
    "一带一路": ["基建出海", "国际工程", "一带一路概念", "一带一路板块"],
    "央企改革": ["国企改革", "并购重组", "重组", "央企改革概念", "国企改革板块"],
    "地产链": ["地产", "房地产", "建材", "家居", "地产链概念", "地产板块"],
    "金融": ["券商", "保险", "银行", "金融科技", "金融概念", "金融板块"],
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
