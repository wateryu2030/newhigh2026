#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略3：高科技+消费财报超预期事件驱动策略

策略逻辑：
- 聚焦高科技（研发投入高）和消费（毛利率稳定）标的
- 当财报营收/净利润超分析师预期时买入
- 持有1个月博弈业绩驱动行情
"""
from rqalpha.apis import *
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta


# 策略参数
HOLD_PERIOD = 20  # 持有20个交易日（约1个月）
TECH_RD_THRESHOLD = 0.05  # 高科技研发投入/营收 >5%
TECH_PROFIT_GROWTH_THRESHOLD = 0.20  # 净利润同比增速超预期>20%
CONSUME_GROSS_MARGIN_THRESHOLD = 0.30  # 消费毛利率>30%
CONSUME_REVENUE_GROWTH_THRESHOLD = 0.10  # 营收同比增速超预期>10%
MAX_POSITION_RATIO = 0.15  # 单标的最大仓位15%


def init(context):
    """初始化"""
    logger.info("策略3：财报超预期事件驱动策略初始化")
    
    # 事件触发记录（股票代码: 买入日期）
    context.event_positions = {}
    
    # 股票池：从数据文件加载，与策略2共用 tech/consume 池
    data_dir = "data"
    tech_path = os.path.join(data_dir, "tech_leader_stocks.csv")
    consume_path = os.path.join(data_dir, "consume_leader_stocks.csv")
    if os.path.exists(tech_path):
        tech_df = pd.read_csv(tech_path, encoding="utf-8-sig")
        context.tech_stocks = tech_df["代码"].tolist() if "代码" in tech_df.columns else []
    else:
        context.tech_stocks = ["000001.XSHE", "000002.XSHE"]
    if os.path.exists(consume_path):
        consume_df = pd.read_csv(consume_path, encoding="utf-8-sig")
        context.consume_stocks = consume_df["代码"].tolist() if "代码" in consume_df.columns else []
    else:
        context.consume_stocks = ["600519.XSHG", "000858.XSHE"]
    all_stocks = list(set(context.tech_stocks + context.consume_stocks))
    if all_stocks:
        update_universe(all_stocks)
    
    # 模拟财报超预期事件（实际应从AKShare获取财报数据）
    context.earnings_surprise_events = load_earnings_events()


def load_earnings_events():
    """加载财报超预期事件（简化版，实际应从AKShare获取）"""
    # 这里返回模拟数据，实际应从数据文件或API获取
    events = {
        # "000001.XSHE": {"date": "2024-01-15", "type": "tech", "surprise": True},
    }
    return events


def before_trading(context):
    """盘前处理"""
    # 检查是否有新的财报超预期事件
    check_earnings_events(context)


def handle_bar(context, bar_dict):
    """处理bar数据"""
    # 检查持仓是否到期
    check_hold_period(context, bar_dict)
    
    # 检查是否有新的买入信号
    check_buy_signals(context, bar_dict)


def check_earnings_events(context):
    """检查财报超预期事件（简化版）"""
    # 实际应从AKShare获取最新财报数据
    # 这里使用模拟逻辑
    pass


def check_buy_signals(context, bar_dict):
    """检查买入信号"""
    # 检查高科技股票
    for stock in context.tech_stocks:
        if stock not in bar_dict:
            continue
        
        if stock in context.event_positions:
            continue  # 已持仓
        
        # 模拟检查财报超预期（实际应从数据获取）
        if should_buy_tech_stock(stock, bar_dict):
            buy_stock(context, stock, "tech")


def should_buy_tech_stock(stock, bar_dict):
    """判断是否买入高科技股票"""
    # 简化版：实际应检查财报数据
    # 1. 研发投入/营收 >5%
    # 2. 净利润同比增速超预期>20%
    # 这里使用模拟逻辑
    return False  # 实际应从财报数据判断


def should_buy_consume_stock(stock, bar_dict):
    """判断是否买入消费股票"""
    # 简化版：实际应检查财报数据
    # 1. 毛利率>30%且同比波动<5%
    # 2. 营收同比增速超预期>10%
    return False  # 实际应从财报数据判断


def buy_stock(context, stock, stock_type):
    """买入股票"""
    try:
        # 计算仓位
        weight = MAX_POSITION_RATIO
        
        # 确保不超过总仓位限制（使用 get_positions API）
        total_value = context.portfolio.total_value
        current_total_weight = 0.0
        if total_value and total_value > 0:
            for pos in get_positions():
                if pos.quantity > 0:
                    current_total_weight += (pos.market_value or 0) / total_value
        
        if current_total_weight + weight > 0.9:  # 总仓位不超过90%
            weight = max(0, 0.9 - current_total_weight)
        
        if weight > 0:
            order_target_percent(stock, weight)
            context.event_positions[stock] = {
                "buy_date": context.now,
                "type": stock_type
            }
            logger.info(f"买入 {stock} ({stock_type}): {weight*100:.2f}%")
    except Exception as e:
        logger.error(f"买入 {stock} 失败: {e}")


def check_hold_period(context, bar_dict):
    """检查持仓是否到期"""
    current_date = context.now
    
    for stock in list(context.event_positions.keys()):
        buy_date = context.event_positions[stock]["buy_date"]
        hold_days = (current_date - buy_date).days
        
        if hold_days >= HOLD_PERIOD:
            # 持仓到期，卖出
            order_target_percent(stock, 0)
            del context.event_positions[stock]
            logger.info(f"持仓到期卖出 {stock}: 持有 {hold_days} 天")


def after_trading(context):
    """盘后处理"""
    pass
