# -*- coding: utf-8 -*-
"""
Skill 11: Chief Risk
风控官。对选出的个股进行二次风控审查
（如是否即将财报雷、是否有巨额解禁、是否短期涨幅过大等），剔除高风险标的
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


# 风控检查项
RISK_CHECKS = {
    "price_spike": {
        "description": "短期涨幅过大",
        "check": lambda s: s.get("price_change_5d", 0) > 25,  # 5天涨25%
        "severity": "high",
    },
    "overbought": {
        "description": "严重超买",
        "check": lambda s: s.get("rsi", 50) > 85,
        "severity": "high",
    },
    "high_volatility": {
        "description": "波动率过高",
        "check": lambda s: s.get("volatility", 0) > 8,  # 日波动>8%
        "severity": "medium",
    },
    "below_ma60": {
        "description": "跌破MA60",
        "check": lambda s: s.get("price_vs_ma60", 0) < -10,
        "severity": "medium",
    },
    "weak_trend": {
        "description": "趋势弱势",
        "check": lambda s: s.get("trend") == "bearish",
        "severity": "medium",
    },
}


def _check_risk(stock: Dict) -> List[Dict[str, Any]]:
    """检查个股风险"""
    risks = []
    
    for risk_name, risk_def in RISK_CHECKS.items():
        try:
            if risk_def["check"](stock):
                risks.append({
                    "type": risk_name,
                    "description": risk_def["description"],
                    "severity": risk_def["severity"],
                })
        except:
            continue
    
    return risks


def execute(ctx) -> Any:
    """
    风控审查
    
    :param ctx: SkillContext
    :return: 更新后的ctx
    """
    picks = ctx.picks
    
    if not picks:
        ctx.risk_filtered_picks = []
        return ctx
    
    risk_filtered = []
    
    for pick in picks:
        risks = _check_risk(pick)
        
        # 统计风险
        high_risks = [r for r in risks if r["severity"] == "high"]
        medium_risks = [r for r in risks if r["severity"] == "medium"]
        
        # 有高风险直接剔除
        if high_risks:
            continue
        
        # 有中风险降低权重
        if medium_risks:
            pick["risk_level"] = "medium"
            pick["risk_warnings"] = [r["description"] for r in medium_risks]
            # 降低买入优先级
            pick["priority"] = pick.get("priority", 10) + len(medium_risks)
        else:
            pick["risk_level"] = "low"
            pick["risk_warnings"] = []
        
        pick["risk_checks"] = risks
        risk_filtered.append(pick)
    
    # 重新排序（考虑风险调整后的优先级）
    risk_filtered.sort(key=lambda x: x.get("priority", 10))
    
    ctx.risk_filtered_picks = risk_filtered
    
    return ctx
