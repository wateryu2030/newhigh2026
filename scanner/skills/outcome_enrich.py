# -*- coding: utf-8 -*-
"""
Skill 13: Outcome Enrich
保存本次运行结果，用于后续的复盘和反馈学习
"""
from __future__ import annotations
import os
import sys
import json
from typing import Any, Dict, List
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def execute(ctx) -> Any:
    """
    保存运行结果
    
    :param ctx: SkillContext
    :return: 更新后的ctx
    """
    # 构建结果数据
    outcome = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "themes_count": len(ctx.themes_with_regime),
        "picks_count": len(ctx.risk_filtered_picks),
        "themes": [
            {
                "name": t.get("name"),
                "stage": t.get("stage_cn"),
                "tier": t.get("tier"),
            }
            for t in ctx.themes_with_regime
        ],
        "picks": [
            {
                "symbol": p.get("symbol"),
                "name": p.get("name"),
                "theme": p.get("theme"),
                "strategy": p.get("strategy"),
                "price": p.get("current_price"),
                "risk_level": p.get("risk_level"),
            }
            for p in ctx.risk_filtered_picks
        ],
        "execution_log": [
            {
                "step": log.get("step"),
                "status": log.get("status"),
                "message": log.get("message"),
            }
            for log in ctx.execution_log
        ],
    }
    
    ctx.outcome = outcome
    
    # 保存到文件
    output_dir = os.path.join(_root, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    outcome_file = os.path.join(output_dir, "scan_outcomes.json")
    
    try:
        # 加载已有结果
        existing = []
        if os.path.exists(outcome_file):
            with open(outcome_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        # 添加新结果
        if not isinstance(existing, list):
            existing = []
        existing.append(outcome)
        
        # 只保留最近60天的结果
        existing = existing[-60:]
        
        # 保存
        with open(outcome_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        
        print(f"[OutcomeEnrich] 结果已保存到 {outcome_file}")
        
    except Exception as e:
        print(f"[OutcomeEnrich] 保存失败: {e}")
    
    return ctx
