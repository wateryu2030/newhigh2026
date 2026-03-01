# -*- coding: utf-8 -*-
"""
Skill 7: Strategy Select
策略路由核心。根据主题的 Tier（梯队：Leaders/Rising/Watch）和 Regime（状态），
为该主题选择最合适的交易策略（如：龙头适合做突破，补涨适合做低吸）
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


# 策略选择规则表
STRATEGY_RULES = {
    # Leaders + 加速期 = 趋势突破
    ("Leaders", "accelerating"): {
        "strategy": "Trend Breakout",
        "strategy_cn": "趋势突破",
        "rationale": "领涨股在加速期，适合突破策略",
        "priority": 1,
    },
    # Leaders + 分歧期 = 回踩反转
    ("Leaders", "divergence"): {
        "strategy": "Pullback Reversal",
        "strategy_cn": "回踩反转",
        "rationale": "龙头股分歧回调，寻找低吸机会",
        "priority": 2,
    },
    # Rising + 启动期 = 低关注度潜伏
    ("Rising", "early"): {
        "strategy": "Low Attention Build",
        "strategy_cn": "低关注度潜伏",
        "rationale": "新兴主题早期，适合潜伏",
        "priority": 3,
    },
    # Rising + 加速期 = 资金跟随
    ("Rising", "accelerating"): {
        "strategy": "Money Follow",
        "strategy_cn": "资金跟随",
        "rationale": "跟风股资金主导，跟随主力",
        "priority": 4,
    },
    # 衰退期 = 均值回归（超跌反弹）
    ("Leaders", "declining"): {
        "strategy": "Mean Reversion Range",
        "strategy_cn": "均值回归",
        "rationale": "衰退期超跌，寻找反弹",
        "priority": 5,
    },
    ("Rising", "declining"): {
        "strategy": "Mean Reversion Range",
        "strategy_cn": "均值回归",
        "rationale": "衰退期超跌，寻找反弹",
        "priority": 5,
    },
}


def _select_strategy_fallback(theme_data: Dict) -> Dict[str, Any]:
    """备用策略选择"""
    tier = theme_data.get("tier", "Rising")
    stage = theme_data.get("stage", "accelerating")
    
    # 查找匹配的规则
    key = (tier, stage)
    if key in STRATEGY_RULES:
        return STRATEGY_RULES[key]
    
    # 默认策略
    return {
        "strategy": "Trend Breakout",
        "strategy_cn": "趋势突破",
        "rationale": "默认选择趋势突破策略",
        "priority": 10,
    }


def execute(ctx, llm_client=None) -> Any:
    """
    为主题选择交易策略
    
    :param ctx: SkillContext
    :param llm_client: LLM客户端
    :return: 更新后的ctx
    """
    themes = ctx.themes_with_regime
    
    if not themes:
        ctx.strategy_plan = {}
        return ctx
    
    strategy_plan = {}
    
    for theme_data in themes:
        theme_name = theme_data["name"]
        
        # 尝试LLM选择，失败则用规则
        if llm_client:
            try:
                llm_result = llm_client.select_strategy_for_theme(
                    theme_name=theme_name,
                    theme_regime=theme_data.get("stage_cn", "加速期"),
                    tier=theme_data.get("tier", "Rising"),
                )
                strategy_info = {
                    "strategy": llm_result.get("strategy", "Trend Breakout"),
                    "strategy_cn": llm_result.get("strategy_cn", "趋势突破"),
                    "rationale": llm_result.get("reason", "LLM推荐"),
                    "priority": 1,
                }
            except Exception as e:
                strategy_info = _select_strategy_fallback(theme_data)
        else:
            strategy_info = _select_strategy_fallback(theme_data)
        
        strategy_plan[theme_name] = {
            **strategy_info,
            "theme_data": theme_data,
        }
    
    ctx.strategy_plan = strategy_plan
    
    return ctx
