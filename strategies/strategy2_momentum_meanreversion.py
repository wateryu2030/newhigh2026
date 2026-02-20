#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
策略2：高科技龙头动量 + 消费龙头均值回归（多因子混合）

策略逻辑：
- 高科技龙头：60日动量策略，选收益率前10%标的，持仓2周
- 消费龙头：均值回归策略，股价偏离20日均线超10%买入，回归卖出
- 仓位分配：高科技60% + 消费40%
"""
from rqalpha.apis import *
import pandas as pd
import numpy as np
import os
from strategies.utils import calculate_ma, calculate_momentum, check_mean_reversion, check_volume_shrinkage, get_top_percent


# 策略参数
MOMENTUM_WINDOW = 60  # 动量周期
MEAN_REVERSION_WINDOW = 20  # 均值回归周期
REBALANCE_INTERVAL = 5  # 周度调仓（5个交易日）
TECH_WEIGHT = 0.6  # 高科技仓位占比
CONSUME_WEIGHT = 0.4  # 消费仓位占比
MOMENTUM_TOP_PERCENT = 0.1  # 动量前10%
MEAN_REVERSION_THRESHOLD = 0.1  # 偏离10%
TAKE_PROFIT_RATIO = 0.15  # 止盈15%
MAX_POSITION_RATIO = 0.2  # 单标的最大仓位20%


def init(context):
    """初始化"""
    logger.info("策略2：动量+均值回归混合策略初始化")
    
    # 加载股票池
    data_dir = "data"
    tech_stocks_path = os.path.join(data_dir, "tech_leader_stocks.csv")
    consume_stocks_path = os.path.join(data_dir, "consume_leader_stocks.csv")
    
    if os.path.exists(tech_stocks_path):
        tech_df = pd.read_csv(tech_stocks_path, encoding="utf-8-sig")
        context.tech_stocks = tech_df["代码"].tolist() if "代码" in tech_df.columns else []
    else:
        logger.warn("未找到高科技股票池，使用默认股票")
        context.tech_stocks = ["000001.XSHE", "000002.XSHE"]  # 示例
    
    if os.path.exists(consume_stocks_path):
        consume_df = pd.read_csv(consume_stocks_path, encoding="utf-8-sig")
        context.consume_stocks = consume_df["代码"].tolist() if "代码" in consume_df.columns else []
    else:
        logger.warn("未找到消费股票池，使用默认股票")
        context.consume_stocks = ["600519.XSHG", "000858.XSHE"]  # 示例
    
    # 将所有股票池加入 universe，这样 bar_dict 中才会有这些股票的数据
    all_stocks = list(set(context.tech_stocks + context.consume_stocks))
    if all_stocks:
        update_universe(all_stocks)
        logger.info(f"已加入 {len(all_stocks)} 只股票到 universe: {all_stocks}")
    
    context.weekly_count = 0
    context.tech_positions = {}  # 高科技持仓
    context.consume_positions = {}  # 消费持仓


def before_trading(context):
    """盘前处理"""
    pass


def handle_bar(context, bar_dict):
    """处理bar数据"""
    context.weekly_count += 1
    
    # 周度调仓
    if context.weekly_count % REBALANCE_INTERVAL == 0:
        rebalance(context, bar_dict)
    
    # 止盈检查
    check_take_profit(context, bar_dict)


def rebalance(context, bar_dict):
    """调仓逻辑"""
    logger.info("执行周度调仓")
    
    # 1. 高科技动量选股
    tech_momentum_stocks = select_tech_momentum(context, bar_dict)
    logger.info(f"高科技动量股票: {tech_momentum_stocks}")
    
    # 2. 消费均值回归选股
    consume_mean_reversion_stocks = select_consume_mean_reversion(context, bar_dict)
    logger.info(f"消费均值回归股票: {consume_mean_reversion_stocks}")
    
    # 3. 调仓
    adjust_position(context, bar_dict, tech_momentum_stocks, consume_mean_reversion_stocks)


def select_tech_momentum(context, bar_dict):
    """高科技动量选股（60日收益率前10%）"""
    stock_returns = []
    
    for stock in context.tech_stocks:
        if stock not in bar_dict:
            continue
        
        try:
            # 获取60日行情
            hist = history_bars(stock, MOMENTUM_WINDOW, "1d", "close")
            if len(hist) < MOMENTUM_WINDOW:
                continue
            
            # 计算60日收益率
            return_rate = calculate_momentum(hist, MOMENTUM_WINDOW)
            if not np.isnan(return_rate):
                stock_returns.append((stock, return_rate))
        except Exception as e:
            logger.debug(f"计算 {stock} 动量失败: {e}")
            continue
    
    # 前10%标的
    top_stocks = get_top_percent(stock_returns, MOMENTUM_TOP_PERCENT)
    return [stock for stock, _ in top_stocks]


def select_consume_mean_reversion(context, bar_dict):
    """消费均值回归选股"""
    target_stocks = []
    
    for stock in context.consume_stocks:
        if stock not in bar_dict:
            continue
        
        try:
            # 20日均线
            hist_close = history_bars(stock, MEAN_REVERSION_WINDOW, "1d", "close")
            if len(hist_close) < MEAN_REVERSION_WINDOW:
                continue
            
            ma20 = calculate_ma(hist_close, MEAN_REVERSION_WINDOW)
            if np.isnan(ma20):
                continue
            
            current_price = bar_dict[stock].close
            
            # 成交量缩量
            hist_vol = history_bars(stock, MEAN_REVERSION_WINDOW, "1d", "volume")
            if len(hist_vol) < MEAN_REVERSION_WINDOW:
                continue
            
            ma20_vol = calculate_ma(hist_vol, MEAN_REVERSION_WINDOW)
            current_vol = bar_dict[stock].volume
            
            # 偏离20日均线超10% + 缩量
            if check_mean_reversion(current_price, ma20, MEAN_REVERSION_THRESHOLD) and \
               check_volume_shrinkage(current_vol, ma20_vol):
                target_stocks.append(stock)
        except Exception as e:
            logger.debug(f"计算 {stock} 均值回归失败: {e}")
            continue
    
    return target_stocks


def adjust_position(context, bar_dict, tech_stocks, consume_stocks):
    """调整仓位"""
    # 清空非目标股票（使用 get_positions API）
    all_target_stocks = tech_stocks + consume_stocks
    for pos in get_positions():
        stock = pos.order_book_id
        if stock not in all_target_stocks:
            order_target_percent(stock, 0)
    
    # 高科技股票等权配置
    if len(tech_stocks) > 0:
        tech_weight_per_stock = min(TECH_WEIGHT / len(tech_stocks), MAX_POSITION_RATIO)
        for stock in tech_stocks:
            order_target_percent(stock, tech_weight_per_stock)
            logger.info(f"配置高科技 {stock}: {tech_weight_per_stock*100:.2f}%")
    
    # 消费股票等权配置
    if len(consume_stocks) > 0:
        consume_weight_per_stock = min(CONSUME_WEIGHT / len(consume_stocks), MAX_POSITION_RATIO)
        for stock in consume_stocks:
            order_target_percent(stock, consume_weight_per_stock)
            logger.info(f"配置消费 {stock}: {consume_weight_per_stock*100:.2f}%")


def check_take_profit(context, bar_dict):
    """止盈检查（使用 get_positions API）"""
    for position in get_positions():
        if position.quantity == 0:
            continue
        stock = position.order_book_id
        cost_price = position.avg_price
        if cost_price == 0:
            continue
        
        try:
            current_price = bar_dict[stock].close
            profit_ratio = (current_price - cost_price) / cost_price
            
            if profit_ratio >= TAKE_PROFIT_RATIO:
                order_target_percent(stock, 0)
                logger.info(f"止盈卖出 {stock}: 盈利 {profit_ratio*100:.2f}%")
        except:
            continue


def after_trading(context):
    """盘后处理"""
    pass
