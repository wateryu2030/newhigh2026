# -*- coding: utf-8 -*-
"""
Skill 6: Theme Stock Bridge
建立"主题-个股"映射。根据本地数据库找到属于该主题的成分股，并加载个股的基础行情数据
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


# 主题-股票映射表（简化版）
# 实际生产环境应该从数据库或外部API获取
THEME_STOCK_MAP = {
    "低空经济": ["002594", "300076", "002151", "002236", "600038"],
    "人工智能": ["000938", "002230", "300496", "002236", "000977"],
    "机器人": ["002896", "300024", "002527", "002559", "300124"],
    "半导体": ["603501", "002371", "300661", "600584", "603933"],
    "华为概念": ["002371", "000938", "300496", "002594", "600584"],
    "鸿蒙": ["300339", "300598", "002512", "300339", "300598"],
    "新能源": ["002594", "300750", "601012", "600438", "300274"],
    "光伏": ["601012", "600438", "300274", "002459", "600732"],
    "储能": ["300274", "002594", "300750", "300014", "002121"],
    "锂电池": ["002594", "300750", "300014", "002460", "002709"],
    "元宇宙": ["300339", "300459", "002624", "300418", "300031"],
    "自动驾驶": ["002594", "300496", "002151", "002405", "002236"],
    "生物医药": ["600276", "000538", "300003", "300122", "002007"],
    "数字经济": ["300339", "000938", "600756", "300229", "300212"],
    "闻泰科技": ["600745"],  # 个股主题
    "易华录": ["300212"],
    "贵州茅台": ["600519"],
}


def _get_stocks_for_theme(theme_name: str) -> List[str]:
    """获取主题对应的股票列表"""
    # 直接匹配
    if theme_name in THEME_STOCK_MAP:
        return THEME_STOCK_MAP[theme_name]
    
    # 尝试别名匹配
    from scanner.skills.canonicalize import THEME_ALIASES
    for canonical, aliases in THEME_ALIASES.items():
        if theme_name in aliases and canonical in THEME_STOCK_MAP:
            return THEME_STOCK_MAP[canonical]
    
    return []


def execute(ctx) -> Any:
    """
    建立主题-股票映射
    
    :param ctx: SkillContext
    :return: 更新后的ctx
    """
    themes = ctx.themes_with_regime
    
    if not themes:
        ctx.theme_stock_map = {}
        return ctx
    
    theme_stock_map = {}
    
    for theme_data in themes:
        theme_name = theme_data["name"]
        stocks = _get_stocks_for_theme(theme_name)
        
        if stocks:
            theme_stock_map[theme_name] = stocks
    
    ctx.theme_stock_map = theme_stock_map
    
    return ctx
