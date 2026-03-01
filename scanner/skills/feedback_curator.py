# -*- coding: utf-8 -*-
"""
Skill 9: Feedback Curator
读取历史运行结果和反馈，构建"负面清单"或"经验库"，
避免重复犯错（如避免在某类行情下反复推荐失效策略）
"""
from __future__ import annotations
import os
import sys
import json
from typing import Any, Dict, List
from datetime import datetime, timedelta

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def _load_historical_outcomes() -> List[Dict[str, Any]]:
    """加载历史运行结果"""
    # 从文件加载历史结果
    outcome_file = os.path.join(_root, "output", "scan_outcomes.json")
    
    if not os.path.exists(outcome_file):
        return []
    
    try:
        with open(outcome_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def _analyze_failures(outcomes: List[Dict]) -> Dict[str, Any]:
    """分析失败模式，构建负面清单"""
    failures = {
        "strategy_failures": {},  # 哪些策略经常失败
        "theme_failures": {},     # 哪些主题经常表现差
        "market_condition_warnings": [],  # 市场状态下的警告
    }
    
    for outcome in outcomes:
        # 只分析最近30天的
        date_str = outcome.get("date", "")
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if (datetime.now() - date).days > 30:
                continue
        except:
            continue
        
        picks = outcome.get("picks", [])
        for pick in picks:
            strategy = pick.get("strategy", "")
            theme = pick.get("theme", "")
            result = pick.get("result", {})  # 假设有结果追踪
            
            if result.get("failed", False):
                # 记录策略失败
                if strategy:
                    failures["strategy_failures"][strategy] = \
                        failures["strategy_failures"].get(strategy, 0) + 1
                
                # 记录主题失败
                if theme:
                    failures["theme_failures"][theme] = \
                        failures["theme_failures"].get(theme, 0) + 1
    
    return failures


def execute(ctx) -> Any:
    """
    加载历史反馈
    
    :param ctx: SkillContext
    :return: 更新后的ctx
    """
    # 加载历史结果
    outcomes = _load_historical_outcomes()
    
    # 分析失败模式
    feedback_data = _analyze_failures(outcomes)
    
    # 添加一些规则化的经验
    feedback_data["rules"] = {
        # 避免在以下情况下推荐
        "avoid_when": [
            {"condition": "rsi > 85", "reason": "严重超买，追高风险大"},
            {"condition": "turnover > 40%", "reason": "换手率过高，投机性强"},
            {"condition": "limit_up_count >= 3", "reason": "连续涨停，随时可能开板"},
            {"condition": "strategy=Trend Breakout AND market=declining", 
             "reason": "衰退期不做突破"},
        ],
        # 优先考虑的信号
        "prefer_when": [
            {"condition": "rsi 40-60 AND volume_expanding", 
             "reason": "RSI健康且量能配合"},
            {"condition": "golden_cross AND price_above_ma20", 
             "reason": "金叉且站稳均线"},
        ],
    }
    
    ctx.feedback_data = feedback_data
    
    return ctx
