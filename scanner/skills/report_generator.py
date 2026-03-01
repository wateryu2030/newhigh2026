# -*- coding: utf-8 -*-
"""
Skill 12: Report Generator
将所有分析结果汇总，生成 Markdown 格式的投资研报
"""
from __future__ import annotations
import os
import sys
from typing import Any, Dict, List
from datetime import datetime

_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)


def _format_stock_table(picks: List[Dict]) -> str:
    """格式化股票表格"""
    if not picks:
        return "暂无推荐标的。\n"
    
    lines = [
        "| 代码 | 名称 | 主题 | 策略 | 价格 | RSI | 止损 | 风险 | 逻辑 |",
        "|------|------|------|------|------|-----|------|------|------|",
    ]
    
    for pick in picks:
        symbol = pick.get("symbol", "")
        name = pick.get("name", symbol)
        theme = pick.get("theme", "")
        strategy = pick.get("strategy_cn", pick.get("strategy", ""))
        price = pick.get("current_price", 0)
        rsi = pick.get("rsi", 0)
        stop_loss = pick.get("stop_loss", "")
        risk = pick.get("risk_level", "medium")
        logic = pick.get("logic", "")[:30] + "..." if len(pick.get("logic", "")) > 30 else pick.get("logic", "")
        
        lines.append(f"| {symbol} | {name} | {theme} | {strategy} | {price} | {rsi} | {stop_loss} | {risk} | {logic} |")
    
    return "\n".join(lines) + "\n"


def _format_theme_summary(themes: List[Dict]) -> str:
    """格式化主题摘要"""
    if not themes:
        return "暂无热点主题。\n"
    
    lines = ["### 热门主题生命周期\n"]
    
    for theme in themes[:5]:  # 只显示前5个
        name = theme.get("name", "")
        stage = theme.get("stage_cn", "未知")
        tier = theme.get("tier", "")
        confidence = theme.get("confidence", 0)
        reason = theme.get("reason", "")
        
        lines.append(f"- **{name}** ({tier}) - {stage} (置信度: {confidence:.0%})")
        lines.append(f"  - {reason}\n")
    
    return "\n".join(lines) + "\n"


def execute(ctx) -> Any:
    """
    生成投资研报
    
    :param ctx: SkillContext
    :return: 更新后的ctx
    """
    # 收集数据
    themes = ctx.themes_with_regime
    picks = ctx.risk_filtered_picks
    exec_log = ctx.execution_log
    
    # 构建报告
    report_lines = [
        f"# 量化投资研报",
        f"",
        f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"---",
        f"",
        f"## 一、市场热点扫描",
        f"",
        _format_theme_summary(themes),
        f"---",
        f"",
        f"## 二、精选标的",
        f"",
        _format_stock_table(picks),
        f"",
        f"### 策略说明",
        f"",
        f"- **趋势突破**: 适合加速期的领涨股，寻找突破关键阻力位的个股",
        f"- **回踩反转**: 适合上升期的分歧回调，寻找缩量回调后企稳的个股",
        f"- **均值回归**: 适合震荡期的低吸，寻找超跌反弹机会",
        f"- **资金跟随**: 跟随主力资金流向，寻找资金持续净流入的个股",
        f"- **低关注度潜伏**: 寻找底部抬升但未被市场广泛挖掘的标的",
        f"",
        f"---",
        f"",
        f"## 三、风险提示",
        f"",
        f"1. 以上分析基于历史数据和量化因子，不构成投资建议",
        f"2. 请严格遵守止损纪律，个股止损位已标注",
        f"3. 高风险和中风险标的需谨慎参与",
        f"4. 市场环境变化可能导致策略失效",
        f"",
        f"---",
        f"",
        f"## 四、执行日志",
        f"",
    ]
    
    # 添加执行日志
    for log in exec_log:
        step = log.get("step", "")
        status = log.get("status", "")
        msg = log.get("message", "")
        report_lines.append(f"- [{status.upper()}] {step}: {msg}")
    
    report = "\n".join(report_lines)
    
    ctx.report = report
    
    return ctx
