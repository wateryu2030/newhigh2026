# -*- coding: utf-8 -*-
"""
Skill 10: Stock Pick
核心选股环节。结合策略指令、量化因子和 LLM 的定性分析，
从候选池中精选个股，并生成交易计划（买入条件、止损位、逻辑）
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


# 策略筛选规则
STRATEGY_FILTERS = {
    "Trend Breakout": {
        "min_rsi": 50,
        "max_rsi": 80,
        "min_price_vs_ma20": -5,  # 允许略微跌破
        "max_price_vs_ma20": 20,
        "required_golden_cross": False,  # 不强求金叉
    },
    "Pullback Reversal": {
        "min_rsi": 30,
        "max_rsi": 60,
        "min_price_vs_ma20": -10,
        "max_price_vs_ma20": 5,  # 接近或略高于MA20
        "required_trend": "bullish",
    },
    "Mean Reversion Range": {
        "min_rsi": 20,
        "max_rsi": 45,
        "min_price_vs_ma60": -15,
        "max_price_vs_ma60": 0,
    },
    "Money Follow": {
        "min_rsi": 40,
        "max_rsi": 70,
    },
    "Low Attention Build": {
        "min_rsi": 35,
        "max_rsi": 55,
        "max_volatility": 3,  # 低波动
    },
    "Event Momentum": {
        "min_rsi": 50,
        "max_rsi": 85,
    },
}


# 放宽版筛选规则（用于 relaxed 模式）
RELAXED_FILTERS = {
    "Trend Breakout": {"min_rsi": 40, "max_rsi": 90, "min_price_vs_ma20": -10, "max_price_vs_ma20": 30},
    "Pullback Reversal": {"min_rsi": 25, "max_rsi": 70, "min_price_vs_ma20": -15, "max_price_vs_ma20": 10},
    "Mean Reversion Range": {"min_rsi": 15, "max_rsi": 55, "min_price_vs_ma60": -20, "max_price_vs_ma60": 5},
    "Money Follow": {"min_rsi": 35, "max_rsi": 80},
    "Low Attention Build": {"min_rsi": 30, "max_rsi": 65, "max_volatility": 5},
    "Event Momentum": {"min_rsi": 45, "max_rsi": 95},
}


def _passes_strategy_filter(stock: Dict, strategy: str, feedback: Dict, relaxed: bool = False) -> bool:
    """检查股票是否满足策略筛选条件
    
    :param relaxed: 是否使用放宽的过滤条件
    """
    rules = RELAXED_FILTERS.get(strategy, {}) if relaxed else STRATEGY_FILTERS.get(strategy, {})
    
    # 检查负面清单
    rsi = stock.get("rsi", 50)
    if rules.get("min_rsi") and rsi < rules["min_rsi"]:
        return False
    if rules.get("max_rsi") and rsi > rules["max_rsi"]:
        return False
    
    price_vs_ma20 = stock.get("price_vs_ma20", 0)
    if rules.get("min_price_vs_ma20") and price_vs_ma20 < rules["min_price_vs_ma20"]:
        return False
    if rules.get("max_price_vs_ma20") and price_vs_ma20 > rules["max_price_vs_ma20"]:
        return False
    
    price_vs_ma60 = stock.get("price_vs_ma60", 0)
    if rules.get("min_price_vs_ma60") and price_vs_ma60 < rules["min_price_vs_ma60"]:
        return False
    if rules.get("max_price_vs_ma60") and price_vs_ma60 > rules["max_price_vs_ma60"]:
        return False
    
    # 检查历史反馈中的避免规则（宽松模式下忽略部分规则）
    if not relaxed:
        avoid_rules = feedback.get("rules", {}).get("avoid_when", [])
        for rule in avoid_rules:
            condition = rule.get("condition", "")
            # 简单条件判断
            if "rsi > 85" in condition and rsi > 85:
                return False
            if "turnover > 40%" in condition:
                # 这里需要换手率数据，简化处理
                pass
    
    return True


def execute(ctx, llm_client=None, top_n: int = 20, relaxed_filter: bool = False) -> Any:
    """
    核心选股
    
    :param ctx: SkillContext
    :param llm_client: LLM客户端
    :param top_n: 选股数量上限
    :param relaxed_filter: 是否使用放宽的过滤条件
    :return: 更新后的ctx
    """
    strategy_plan = ctx.strategy_plan
    enriched_data = ctx.enriched_data
    feedback = ctx.feedback_data
    
    if not strategy_plan or not enriched_data:
        ctx.picks = []
        ctx.candidates_count = 0
        ctx.filtered_count = 0
        return ctx
    
    picks = []
    candidates_count = 0
    filtered_count = 0
    
    for theme, strategy_info in strategy_plan.items():
        strategy = strategy_info["strategy"]
        stocks = enriched_data.get(theme, [])
        
        for stock in stocks:
            candidates_count += 1
            # 硬性过滤
            if not _passes_strategy_filter(stock, strategy, feedback, relaxed=relaxed_filter):
                filtered_count += 1
                continue
            
            # 准备LLM分析数据
            stock_data = {
                **stock,
                "theme": theme,
                "strategy": strategy,
            }
            
            # LLM深度分析（可选）
            if llm_client:
                try:
                    llm_result = llm_client.analyze_stock_for_pick(stock_data, strategy)
                    if not llm_result.get("pass", True):
                        continue
                    
                    pick = {
                        **stock,
                        "theme": theme,
                        "strategy": strategy,
                        "strategy_cn": strategy_info.get("strategy_cn", ""),
                        "logic": llm_result.get("logic", ""),
                        "stop_loss": llm_result.get("stop_loss", "MA20下方5%"),
                        "observe": llm_result.get("observe", "次日开盘"),
                        "risk": llm_result.get("risk", "medium"),
                        "priority": strategy_info.get("priority", 10),
                    }
                except:
                    # LLM失败使用默认逻辑
                    pick = {
                        **stock,
                        "theme": theme,
                        "strategy": strategy,
                        "strategy_cn": strategy_info.get("strategy_cn", ""),
                        "logic": f"符合{strategy}策略",
                        "stop_loss": "MA20下方5%",
                        "observe": "次日开盘",
                        "risk": "medium",
                        "priority": strategy_info.get("priority", 10),
                    }
            else:
                # 无LLM使用默认逻辑
                pick = {
                    **stock,
                    "theme": theme,
                    "strategy": strategy,
                    "strategy_cn": strategy_info.get("strategy_cn", ""),
                    "logic": f"符合{strategy}策略",
                    "stop_loss": "MA20下方5%",
                    "observe": "次日开盘",
                    "risk": "medium" if 40 <= stock.get("rsi", 50) <= 70 else "high",
                    "priority": strategy_info.get("priority", 10),
                }
            
            picks.append(pick)
    
    # 按优先级和综合得分排序
    picks.sort(key=lambda x: (x.get("priority", 10), -x.get("rsi", 50)), reverse=False)
    
    ctx.picks = picks[:top_n]
    ctx.candidates_count = candidates_count
    ctx.filtered_count = filtered_count
    
    return ctx
