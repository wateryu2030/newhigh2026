# -*- coding: utf-8 -*-
"""
Skill 5: Theme Regime
判定主题当前所处的生命周期阶段（启动、加速、分歧、衰退/过热）
结合资金流、涨幅、情绪等因子进行判断
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


# 主题生命周期定义
REGIME_STAGES = {
    "early": "启动期",
    "accelerating": "加速期", 
    "divergence": "分歧期",
    "declining": "衰退期",
}


def _analyze_regime_fallback(theme_data: Dict) -> Dict[str, Any]:
    """备用：基于简单规则判定生命周期"""
    # 从新闻情感判断
    sentiment_scores = []
    for news in theme_data.get("news", []):
        label = news.get("sentiment_label", "neutral")
        if label == "positive":
            sentiment_scores.append(1)
        elif label == "negative":
            sentiment_scores.append(-1)
        else:
            sentiment_scores.append(0)
    
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    mention_count = theme_data.get("mention_count", 0)
    
    # 简单规则判断
    if mention_count < 3 and avg_sentiment > 0:
        return {
            "stage": "early",
            "stage_cn": "启动期",
            "confidence": 0.6,
            "reason": "提及次数较少，情绪正面，处于启动阶段",
        }
    elif mention_count >= 5 and avg_sentiment > 0.3:
        return {
            "stage": "accelerating",
            "stage_cn": "加速期", 
            "confidence": 0.7,
            "reason": "提及频繁，情绪高涨，处于加速阶段",
        }
    elif mention_count >= 5 and abs(avg_sentiment) < 0.2:
        return {
            "stage": "divergence",
            "stage_cn": "分歧期",
            "confidence": 0.6,
            "reason": "提及多但情绪分化，处于分歧阶段",
        }
    elif avg_sentiment < -0.2:
        return {
            "stage": "declining",
            "stage_cn": "衰退期",
            "confidence": 0.5,
            "reason": "情绪转负，热度下降",
        }
    else:
        return {
            "stage": "accelerating",
            "stage_cn": "加速期",
            "confidence": 0.5,
            "reason": "默认判断",
        }


def execute(ctx, llm_client=None, top_n: int = 10) -> Any:
    """
    判定主题生命周期阶段
    
    :param ctx: SkillContext
    :param llm_client: LLM客户端
    :param top_n: 保留前N个主题
    :return: 更新后的ctx
    """
    validated = ctx.themes_validated
    
    if not validated:
        ctx.themes_with_regime = []
        return ctx
    
    themes_with_regime = []
    
    for theme_data in validated[:top_n]:
        theme_name = theme_data["name"]
        
        # 收集该主题相关的新闻
        theme_news = [
            news for news in ctx.news_raw
            if theme_name in news.get("title", "") or theme_name in news.get("content", "")
        ]
        
        # 准备主题数据
        theme_info = {
            "name": theme_name,
            "mention_count": theme_data.get("mention_count", 0),
            "news": theme_news,
        }
        
        # 尝试使用LLM分析，失败则用备用方案
        if llm_client:
            try:
                # 这里简化处理，使用情感平均作为模拟的资金流和情绪
                sentiments = [1 if n.get("sentiment_label") == "positive" else 
                             -1 if n.get("sentiment_label") == "negative" else 0 
                             for n in theme_news]
                avg_sentiment = sum(sentiments) / len(sentiments) * 50 + 50 if sentiments else 50
                
                regime_result = llm_client.analyze_theme_regime(
                    theme_name=theme_name,
                    fund_flow=avg_sentiment,  # 用情感作为资金流的代理
                    price_change=5.0 if avg_sentiment > 50 else -2.0,
                    sentiment=avg_sentiment,
                )
            except Exception as e:
                regime_result = _analyze_regime_fallback(theme_info)
        else:
            regime_result = _analyze_regime_fallback(theme_info)
        
        themes_with_regime.append({
            **theme_data,
            **regime_result,
            "tier": "Leaders" if regime_result.get("stage") == "accelerating" else "Rising",
        })
    
    ctx.themes_with_regime = themes_with_regime
    
    return ctx
