# -*- coding: utf-8 -*-
"""
Skill 2: Theme Heat
利用 LLM 或新闻检测从新闻中提取热门概念和行业主题；支持基于关键词与基于新闻文本自动发现主题。
"""
from __future__ import annotations
import os
import sys
import re
from typing import Any, List, Dict
from collections import Counter

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


# 预定义主题关键词（扩展版，用于从新闻中匹配并形成主题，不限于单一人工智能）
THEME_KEYWORDS = {
    "低空经济": ["低空", "飞行汽车", "eVTOL", "通用航空", "低空飞行"],
    "人工智能": ["AI", "人工智能", "大模型", "GPT", "ChatGPT", "AIGC", "生成式AI", "Sora", "Kimi", "Claude"],
    "算力": ["算力", "AI算力", "智算", "算力租赁", "算力基础设施", "CPO", "液冷", "铜缆"],
    "人形机器人": ["人形机器人", "具身智能", "仿生机器人", "仿人机器人", "机器人"],
    "半导体": ["半导体", "芯片", "集成电路", "IC", "光刻胶", "光刻机", "国产替代"],
    "华为概念": ["华为", "鸿蒙", "欧拉", "昇腾", "华为产业链", "华为链"],
    "鸿蒙": ["鸿蒙", "HarmonyOS", "鸿蒙系统"],
    "新能源": ["新能源", "清洁能源", "可再生能源", "绿色能源"],
    "光伏": ["光伏", "太阳能", "光伏发电", "硅片", "组件"],
    "风电": ["风电", "海上风电", "风机", "叶片"],
    "储能": ["储能", "储能电池", "电化学储能", "新型储能"],
    "锂电池": ["锂电池", "动力电池", "锂离子电池", "固态电池", "锂矿"],
    "氢能": ["氢能", "氢燃料电池", "绿氢", "制氢"],
    "数字经济": ["数字经济", "数据要素", "数据确权", "数字化", "产业数字化"],
    "信创": ["信创", "国产软件", "国产替代", "数据安全", "网络安全"],
    "元宇宙": ["元宇宙", "Metaverse", "VR", "AR", "虚拟现实", "MR", "混合现实"],
    "消费电子": ["消费电子", "折叠屏", "MR", "苹果产业链", "手机链"],
    "自动驾驶": ["自动驾驶", "无人驾驶", "智能驾驶", "智能网联汽车", "车联网"],
    "生物医药": ["医药", "创新药", "CXO", "疫苗", "生物医药", "中药"],
    "军工": ["军工", "航天", "航空", "导弹", "军品"],
    "卫星": ["卫星", "卫星互联网", "星链", "低轨卫星"],
    "特高压": ["特高压", "电网", "输配电", "特高压电网"],
    "充电桩": ["充电桩", "充电", "换电", "充电网络"],
    "消费复苏": ["消费复苏", "白酒", "食品饮料", "家电", "零售", "餐饮"],
    "高股息": ["高股息", "分红", "红利", "股息率"],
    "出口链": ["出口", "出海", "外销", "出口链"],
    "一带一路": ["一带一路", "基建出海", "国际工程"],
    "央企改革": ["央企改革", "国企改革", "并购重组", "重组"],
    "地产链": ["地产", "房地产", "建材", "家居", "地产链"],
    "金融": ["金融", "券商", "保险", "银行", "金融科技"],
}


def _extract_themes_from_news_patterns(news_list: List[Dict]) -> List[str]:
    """
    从新闻正文中按模式自动发现主题（不依赖预定义列表）。
    匹配：XX概念、XX板块、XX龙头、XX产业链、XX行情、XX主题 等，提取 XX 或整短语作为候选主题。
    """
    # 模式：2-10 个字符 + 概念/板块/龙头/产业链/行情/主题/热点
    pattern = re.compile(
        r"([\u4e00-\u9fa5A-Za-z0-9]{2,10})"
        r"(概念|板块|龙头|产业链|行情|主题|热点|题材)"
    )
    seen = set()
    candidates: List[str] = []
    for news in news_list:
        text = f"{news.get('title', '')} {news.get('content', '')}"
        for m in pattern.finditer(text):
            name = m.group(1).strip()
            suffix = m.group(2)
            if len(name) < 2 or name in ("相关", "今日", "本周", "市场", "行业", "公司", "个股"):
                continue
            # 优先用「XX概念」形式，便于与别名表对齐
            full = name + suffix
            if full not in seen:
                seen.add(full)
                candidates.append(full)
            if name not in seen and len(name) >= 2:
                seen.add(name)
                candidates.append(name)
    return candidates


def _extract_themes_fallback(news_list: List[Dict]) -> List[str]:
    """基于关键词 + 新闻模式 提取主题（当 LLM 不可用时），主题更多且来自新闻检测。"""
    theme_scores: Dict[str, float] = {}
    for news in news_list:
        text = f"{news.get('title', '')} {news.get('content', '')}"
        for theme, keywords in THEME_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                theme_scores[theme] = theme_scores.get(theme, 0) + score

    # 从新闻中自动发现的主题（模式匹配）
    pattern_themes = _extract_themes_from_news_patterns(news_list)
    for t in pattern_themes:
        theme_scores[t] = theme_scores.get(t, 0) + 2  # 新闻中显式出现的概念加权

    # 按频次排序，返回更多主题（来自更多新闻时条数增多）
    sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_themes[:40]]


def execute(ctx, llm_client=None) -> Any:
    """
    提取热门主题：优先 LLM，并始终合并「基于新闻检测」自动发现的主题，使主题更多且来自新闻。
    """
    news_texts = [
        f"{n.get('title', '')} {n.get('content', '')}"
        for n in ctx.news_raw
    ]

    if not news_texts:
        ctx.themes_raw = []
        return ctx

    # 始终基于新闻做关键词+模式提取（新闻驱动）
    news_driven = _extract_themes_fallback(ctx.news_raw)

    themes: List[str] = []
    if llm_client:
        try:
            llm_themes = llm_client.extract_themes(news_texts)
            themes = [t.get("name", "").strip() for t in llm_themes if t.get("name")]
        except Exception as e:
            print(f"[ThemeHeat] LLM提取失败，使用新闻检测方案: {e}")
    # 合并：LLM 结果 + 新闻检测结果，去重并保持顺序（新闻检测补充更多）
    seen = set()
    for t in themes:
        if t and t not in seen:
            seen.add(t)
    for t in news_driven:
        if t and t not in seen:
            seen.add(t)
            themes.append(t)
    if not themes:
        themes = news_driven

    ctx.themes_raw = themes
    return ctx
